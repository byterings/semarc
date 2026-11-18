"""Builds a target-neutral API scenario from Architecture IR.

The scenario is a deterministic list of HTTP steps that exercises the generated
API: authentication, CRUD operations, validation, conflicts and access control.
Every target ships a runner for it, and SEMARC's end-to-end check replays the
same scenario against a live server.

Step format:
    name     human readable label
    method   HTTP method
    path     concrete path; ${var} is replaced with a saved value
    auth     send the saved bearer token
    auth_as  name of the saved token to send instead of "token"
    body     JSON body; {"$ref": "var"} is replaced with a saved value
    expect   expected HTTP status, or a list of acceptable statuses
    headers  extra request headers
    expect_headers  response headers that must have the given values
    equals   {"dotted.path": value-or-$ref} assertions on the JSON response
    absent   dotted paths that must not exist in the JSON response
    save     {"var": "dotted.path"} values captured from the JSON response
"""
from urllib.parse import urlencode

from semarc.generator.utils.inflector import snake_case
from semarc.generator.utils.resource_views import input_fields, models_in_migration_order, owner_reference, unique_columns

MISSING_ID = 999999
ADMIN_EMAIL = "admin@example.com"  # runners set BOOTSTRAP_ADMIN_EMAIL to this address
CORS_ORIGIN = "https://app.example.com"


class ApiScenarioBuilder:
    def build(self, ir: dict) -> dict:
        self.ir = ir
        self.steps: list[dict] = []
        self.has_token = False
        self.has_admin = False
        self.role_checked: set[tuple[str, str]] = set()
        self.created: list[dict] = []
        self.variants: dict[str, int] = {}

        self._experience_steps()
        self._auth_steps()
        for model in models_in_migration_order(ir):
            self._resource_steps(model)
        self._ownership_steps()
        self._custom_steps()
        self._delete_steps()
        self._rate_limit_steps()
        return {"project": ir["project"], "steps": self.steps}

    def _experience_steps(self) -> None:
        self._step("home page", "GET", "/", 200)
        self._step("health check", "GET", "/health", 200, equals={"status": "ok", "database": "ok"})
        self._step("route discovery", "GET", "/routes", 200)
        self._step("OpenAPI document", "GET", "/openapi.json", 200, equals={"openapi": "3.1.0", "info.title": self.ir["project"], "components.schemas.Error.type": "object"})
        self._step("API documentation page", "GET", "/docs", 200)
        self._step("unknown route", "GET", "/semarc-missing-route", 404)
        self._step(
            "CORS headers on requests from a browser",
            "GET",
            "/health",
            200,
            headers={"Origin": CORS_ORIGIN},
            expect_headers={"access-control-allow-origin": "*"},
        )
        self._step(
            "CORS preflight",
            "OPTIONS",
            "/health",
            [200, 204],
            headers={"Origin": CORS_ORIGIN, "Access-Control-Request-Method": "GET"},
            expect_headers={"access-control-allow-origin": "*"},
        )

    def _auth_steps(self) -> None:
        auth = self.ir.get("auth")
        if not auth:
            return
        user = self._model(auth["model"])
        if any(not reference["owner"] for reference in user["references"]):
            return

        body = self._body(user, include_owner=False)
        identity = body[auth["identity_field"]]
        secret = body[auth["secret_field"]]
        hidden = [f"data.user.{auth['secret_field']}"]

        self._step("register rejects empty body", "POST", "/register", 422, body={})
        self._step(
            "register",
            "POST",
            "/register",
            201,
            body=body,
            equals={f"data.user.{auth['identity_field']}": identity, "data.token_type": "Bearer"},
            absent=hidden,
            save={"token": "data.access_token", "user_id": "data.user.id"},
        )
        self._step("register rejects duplicate identity", "POST", "/register", 409, body=body)
        self._step(
            "login rejects wrong secret",
            "POST",
            "/login",
            401,
            body={auth["identity_field"]: identity, auth["secret_field"]: secret + "-wrong"},
        )
        self._step("login rejects empty body", "POST", "/login", 422, body={})
        self._step(
            "login",
            "POST",
            "/login",
            200,
            body={auth["identity_field"]: identity, auth["secret_field"]: secret},
            equals={"data.token_type": "Bearer"},
            save={"token": "data.access_token"},
        )
        self._step(
            "current user",
            "GET",
            "/me",
            200,
            auth=True,
            equals={"data.id": {"$ref": "user_id"}, f"data.{auth['identity_field']}": identity},
            absent=[f"data.{auth['secret_field']}"],
        )
        self._step("current user requires token", "GET", "/me", 401)
        self._step("current user rejects invalid token", "GET", "/me", 401, token="invalid.token.value")
        self.has_token = True
        self.created.append({"model": user, "var": "user_id", "routes": {}, "parents": set()})
        roles = auth.get("features", {}).get("roles")
        if roles:
            self._role_steps(user, auth, roles)

    def _role_steps(self, user: dict, auth: dict, roles: dict) -> None:
        identity = auth["identity_field"]
        self._step("registered users get the default role", "GET", "/me", 200, auth=True, equals={"data.role": roles["default"]})
        admin = {**self._body(user, include_owner=False), identity: ADMIN_EMAIL}
        self._step(
            "bootstrap admin registers",
            "POST",
            "/register",
            201,
            body=admin,
            equals={"data.user.role": roles["admin"]},
            save={"admin_token": "data.access_token", "admin_id": "data.user.id"},
        )
        self.has_admin = True
        path = "/users/${user_id}/role"
        self._step("changing a role requires admin", "PUT", path, 403, auth=True, body={"role": roles["admin"]})
        self._step("role must be known", "PUT", path, 422, auth=True, auth_as="admin_token", body={"role": "not_a_role"})
        self._step(
            "admin changes a role",
            "PUT",
            path,
            200,
            auth=True,
            auth_as="admin_token",
            body={"role": roles["default"]},
            equals={"data.role": roles["default"], "data.id": {"$ref": "user_id"}},
        )
        self._step("role change for a missing user", "PUT", f"/users/{MISSING_ID}/role", 404, auth=True, auth_as="admin_token", body={"role": roles["default"]})

    def _resource_steps(self, model: dict) -> None:
        routes = self._routes_by_kind(model["name"])
        var = self._record_var(model)
        label = model["name"]

        create = routes.get("create")
        if create is None or not self._can_call(create):
            if "list" in routes and self._can_call(routes["list"]):
                self._call(routes["list"], f"list {label}", 200, path=self._path(routes["list"]))
            return

        protected = create["access"] == "protected"
        references = self._reference_refs(model, include_owner=not protected)
        if references is None:
            if "list" in routes and self._can_call(routes["list"]):
                self._call(routes["list"], f"list {label}", 200, path=self._path(routes["list"]))
            return

        body = {**self._body(model, include_owner=not protected), **references}
        visible = next(
            (
                model_field
                for model_field in model["fields"]
                if not model_field.get("secret", False) and model_field["name"] in body
            ),
            None,
        )
        hidden = [f"data.{name}" for name in self._secret_names(model)]

        if protected:
            self._step(f"create {label} requires token", "POST", self._path(create), 401, body=body)
        if any(rules["required"] for rules in input_fields(model, include_owner=not protected).values()):
            self._call(create, f"create {label} rejects empty body", 422, path=self._path(create), body={})

        equals = {visible["name"]: body[visible["name"]]} if visible else {}
        owner = owner_reference(model)
        if protected and owner and self.has_token:
            equals[owner["column"]] = {"$ref": "user_id"}
        self._call(
            create,
            f"create {label}",
            201,
            path=self._path(create),
            body=body,
            equals={f"data.{key}": value for key, value in equals.items()},
            absent=hidden,
            save={var: "data.id"},
        )
        parents = {value["$ref"] for value in references.values()}
        if protected and owner and self.has_token:
            parents.add("user_id")
        self.created.append({"model": model, "var": var, "routes": routes, "parents": parents, "body": body})

        if unique_columns(model):
            self._call(create, f"create {label} rejects duplicate", 409, path=self._path(create), body=body)

        if "read" in routes:
            read = routes["read"]
            self._call(
                read,
                f"read {label}",
                200,
                path=self._path(read, var),
                equals={f"data.{key}": value for key, value in equals.items()} | {"data.id": {"$ref": var}},
                absent=hidden,
            )
            self._call(read, f"read missing {label}", 404, path=self._path(read, str(MISSING_ID)))

        if "list" in routes:
            self._call(routes["list"], f"list {label}", 200, path=self._path(routes["list"]), equals={"meta.offset": 0})
            self._query_steps(model, routes["list"], body)

        for route in self._routes_of_kind(model["name"], "list_related"):
            parent_var = self._parent_var(route["operation"]["parent_model"])
            if parent_var is not None:
                self._call(route, f"list {label} by {route['operation']['parent_model']}", 200, path=self._path(route, parent_var))

        if "update" in routes:
            self._update_steps(model, routes["update"], var, body)
        if "replace" in routes:
            replacement = {**self._body(model, include_owner=routes["replace"]["access"] != "protected"), **references}
            self._call(
                routes["replace"],
                f"replace {label}",
                200,
                path=self._path(routes["replace"], var),
                body=replacement,
            )

    def _query_steps(self, model: dict, route: dict, body: dict) -> None:
        """Equality filters and sorting on a list route holding exactly one record of this model."""
        auth = self.ir.get("auth")
        if auth and model["name"] == auth["model"]:
            return
        label = model["name"]
        path = self._path(route)
        filters = model.get("query", {}).get("filters", {})
        candidate = next(
            (
                name
                for name, value in body.items()
                if name in filters and filters[name] in {"STRING", "INTEGER", "BOOLEAN", "DATE"} and not isinstance(value, dict)
            ),
            None,
        )
        if candidate is not None:
            value = body[candidate]
            self._call(route, f"filter {label} by {candidate}", 200, path=f"{path}?{urlencode({candidate: _query_text(value)})}", equals={"meta.total": 1})
            self._call(
                route,
                f"filter {label} by {candidate} without matches",
                200,
                path=f"{path}?{urlencode({candidate: _query_text(_other_value(value))})}",
                equals={"meta.total": 0},
            )
        self._call(route, f"sort {label} descending", 200, path=f"{path}?sort=-id", equals={"meta.total": 1})
        self._call(route, f"sort {label} rejects unknown field", 422, path=f"{path}?sort=not_a_field")
        self._call(route, f"filter {label} rejects invalid value", 422, path=f"{path}?id=not-a-number")

    def _update_steps(self, model: dict, route: dict, var: str, body: dict) -> None:
        label = model["name"]
        candidate = next(
            (
                model_field
                for model_field in model["fields"]
                if not model_field.get("secret", False) and not model_field["unique"]
            ),
            None,
        )
        if candidate is not None:
            value = self._sample(candidate, self._next_variant(model["name"]))
            self._call(
                route,
                f"update {label}",
                200,
                path=self._path(route, var),
                body={candidate["name"]: value},
                equals={f"data.{candidate['name']}": value},
            )

        invalid = next((model_field for model_field in model["fields"] if not model_field.get("secret", False)), None)
        if invalid is not None:
            wrong = 12345 if invalid["type"] in {"STRING", "TEXT"} else "not-a-valid-value"
            self._call(
                route,
                f"update {label} rejects invalid value",
                422,
                path=self._path(route, var),
                body={invalid["name"]: wrong},
            )
        self._call(route, f"update missing {label}", 404, path=self._path(route, str(MISSING_ID)), body={})

    def _ownership_steps(self) -> None:
        """A second user must not change records owned by the first one."""
        owned = [
            entry
            for entry in self.created
            if entry["routes"]
            and any(entry["routes"].get(kind, {}).get("operation", {}).get("owner_only") for kind in ("update", "replace", "delete"))
        ]
        if not owned:
            return

        auth = self.ir["auth"]
        user = self._model(auth["model"])
        self._step(
            "register second user",
            "POST",
            "/register",
            201,
            body=self._body(user, include_owner=False),
            save={"other_token": "data.access_token"},
        )
        for entry in owned:
            label = entry["model"]["name"]
            for kind in ("update", "replace", "delete"):
                route = entry["routes"].get(kind)
                if route is None or not route["operation"].get("owner_only"):
                    continue
                body = {"update": {}, "replace": entry["body"], "delete": None}[kind]
                self._step(
                    f"{kind} {label} of another user is forbidden",
                    route["method"],
                    self._path(route, entry["var"]),
                    403,
                    auth=True,
                    auth_as="other_token",
                    body=body,
                )
            if self.has_admin and "update" in entry["routes"] and entry["routes"]["update"]["operation"].get("owner_only"):
                self._step(
                    f"admin may update another user's {label}",
                    "PATCH",
                    self._path(entry["routes"]["update"], entry["var"]),
                    200,
                    auth=True,
                    auth_as="admin_token",
                    body={},
                )

    def _custom_steps(self) -> None:
        for route in self.ir["routes"]:
            if route["operation"]["kind"] != "custom" or not self._can_call(route):
                continue
            path = route["path"]
            for parameter in route["parameters"]:
                path = path.replace("{" + parameter + "}", "1")
            self._call(route, f"custom {route['method']} {route['path']} is not implemented", 501, path=path)

    def _delete_steps(self) -> None:
        deleted = set()
        for entry in self.created:
            delete = entry["routes"].get("delete")
            if delete is None or not self._can_call(delete):
                continue
            if any(entry["var"] in child["parents"] for child in self.created):
                self._call(
                    delete,
                    f"delete {entry['model']['name']} blocked by dependents",
                    409,
                    path=self._path(delete, entry["var"]),
                )

        for entry in reversed(self.created):
            delete = entry["routes"].get("delete")
            if delete is None or not self._can_call(delete):
                continue
            label = entry["model"]["name"]
            if any(entry["var"] in child["parents"] and child["var"] not in deleted for child in self.created):
                continue
            self._call(delete, f"delete {label}", 204, path=self._path(delete, entry["var"]))
            deleted.add(entry["var"])
            if "read" in entry["routes"]:
                self._call(entry["routes"]["read"], f"read deleted {label}", 404, path=self._path(entry["routes"]["read"], entry["var"]))
            self._call(delete, f"delete missing {label}", 404, path=self._path(delete, entry["var"]))

    def _rate_limit_steps(self) -> None:
        """Exceeds the login limit last: afterwards nobody from this client can log in."""
        auth = self.ir.get("auth")
        if not auth or not self.has_token:
            return
        login = next(item for item in self.steps if item["path"] == "/login" and item["expect"] == 200)
        credentials = {**login["body"], auth["secret_field"]: login["body"][auth["secret_field"]] + "-wrong"}
        used = sum(1 for item in self.steps if item["method"] == "POST" and item["path"] == "/login")
        attempts = auth["rate_limit"]["attempts"]

        # Whether a rejected (422) body counts as an attempt is framework specific,
        # so the attempt at the limit may already be refused.
        for index in range(used + 1, attempts):
            self._step(f"login attempt {index} within the rate limit", "POST", "/login", 401, body=credentials)
        self._step(f"login attempt {attempts} at the rate limit", "POST", "/login", [401, 429], body=credentials)
        self._step(
            "login is rate limited",
            "POST",
            "/login",
            429,
            body=credentials,
            equals={"error.code": "too_many_requests"},
        )

    def _body(self, model: dict, include_owner: bool) -> dict:
        variant = self._next_variant(model["name"])
        body = {}
        for model_field in model["fields"]:
            if model_field["required"] or model_field.get("secret", False) or model_field["rules"].get("email"):
                body[model_field["name"]] = self._sample(model_field, variant)
        return body

    def _reference_refs(self, model: dict, include_owner: bool) -> dict | None:
        refs = {}
        for reference in model["references"]:
            if reference["owner"] and not include_owner:
                continue
            var = self._parent_var(reference["model"])
            if var is None:
                return None
            refs[reference["column"]] = {"$ref": var}
        return refs

    def _sample(self, model_field: dict, variant: int):
        rules = model_field.get("rules", {})
        field_type = model_field["type"]
        name = model_field["name"]
        if field_type in {"STRING", "TEXT"}:
            if rules.get("email"):
                value = f"{name.replace('_', '.')}{variant}@example.com"
            elif model_field.get("secret", False):
                value = f"Secret-{variant}-passphrase"
            else:
                value = f"{name} {variant}"
            minimum = rules.get("min") or 0
            if len(value) < minimum:
                value += "x" * (minimum - len(value))
            maximum = rules.get("max")
            if field_type == "STRING":
                maximum = 255 if maximum is None else min(maximum, 255)
            if maximum is not None and len(value) > maximum:
                value = value[:maximum]
            return value
        if field_type == "INTEGER":
            value = (rules.get("min") if rules.get("min") is not None else 1) + variant
            return min(value, rules["max"]) if rules.get("max") is not None else value
        if field_type == "DATE":
            return f"2026-01-{10 + variant % 18:02d}"
        if field_type == "DATETIME":
            return f"2026-01-{10 + variant % 18:02d}T10:30:00Z"
        if field_type == "FLOAT":
            value = (rules.get("min") if rules.get("min") is not None else 1) + variant + 0.5
            return min(value, rules["max"]) if rules.get("max") is not None else value
        return variant % 2 == 1

    def _secret_names(self, model: dict) -> list[str]:
        return [model_field["name"] for model_field in model["fields"] if model_field.get("secret", False)]

    def _routes_by_kind(self, model_name: str) -> dict:
        routes = {}
        for route in self.ir["routes"]:
            operation = route["operation"]
            if operation.get("model") != model_name or operation["kind"].startswith("auth_"):
                continue
            if operation["kind"] in {"custom", "list_related"}:
                continue
            routes.setdefault(operation["kind"], route)
        return routes

    def _routes_of_kind(self, model_name: str, kind: str) -> list[dict]:
        return [
            route
            for route in self.ir["routes"]
            if route["operation"].get("model") == model_name and route["operation"]["kind"] == kind
        ]

    def _path(self, route: dict, value: str | None = None) -> str:
        path = route["path"]
        for parameter in route["parameters"]:
            replacement = value if value is not None else "1"
            if replacement.isdigit():
                path = path.replace("{" + parameter + "}", replacement)
            else:
                path = path.replace("{" + parameter + "}", "${" + replacement + "}")
        return path

    def _can_call(self, route: dict) -> bool:
        return route["access"] == "public" or self.has_token

    def _record_var(self, model: dict) -> str:
        auth = self.ir.get("auth")
        if auth and model["name"] == auth["model"]:
            return f"{snake_case(model['name'])}_record_id"
        return f"{snake_case(model['name'])}_id"

    def _parent_var(self, model_name: str) -> str | None:
        for entry in self.created:
            if entry["model"]["name"] == model_name:
                return entry["var"]
        return None

    def _next_variant(self, model_name: str) -> int:
        self.variants[model_name] = self.variants.get(model_name, 0) + 1
        return self.variants[model_name]

    def _model(self, name: str) -> dict:
        return next(model for model in self.ir["models"] if model["name"] == name)

    def _call(self, route: dict, name: str, expect: int, path: str, body=None, equals=None, absent=None, save=None) -> None:
        auth_as = None
        if route.get("roles") and self.has_admin:
            key = (route["method"], route["path"])
            if key not in self.role_checked:
                self.role_checked.add(key)
                self._step(f"{route['method']} {route['path']} requires role {', '.join(route['roles'])}", route["method"], path, 403, auth=True, body=body)
            auth_as = "admin_token"
        self._step(
            name,
            route["method"],
            path,
            expect,
            auth=route["access"] == "protected",
            body=body,
            equals=equals,
            absent=absent,
            save=save,
            auth_as=auth_as,
        )

    def _step(
        self, name, method, path, expect, auth=False, body=None, equals=None, absent=None, save=None, token=None, auth_as=None,
        headers=None, expect_headers=None,
    ) -> None:
        step = {"name": name, "method": method, "path": path, "expect": expect}
        if headers:
            step["headers"] = headers
        if expect_headers:
            step["expect_headers"] = expect_headers
        if auth:
            step["auth"] = True
        if auth_as:
            step["auth_as"] = auth_as
        if token:
            step["token"] = token
        if body is not None:
            step["body"] = body
        if equals:
            step["equals"] = equals
        if absent:
            step["absent"] = absent
        if save:
            step["save"] = save
        self.steps.append(step)


def _query_text(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _other_value(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1000
    if isinstance(value, str) and len(value) == 10 and value[4] == "-" and value[7] == "-":
        return "1999-01-01"
    return f"{value} none"

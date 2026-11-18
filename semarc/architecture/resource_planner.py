import re

from semarc.architecture.rules.auth_rules import (
    ACCOUNT_STRATEGIES,
    CSRF_COOKIE,
    CSRF_HEADER,
    REFRESH_ROUTE,
    SESSION_COOKIE,
    SESSION_TABLE,
    SESSION_TTL_SECONDS,
    AUTH_IDENTITY_FIELD,
    AUTH_MODEL,
    AUTH_ROUTES,
    AUTH_SECRET_FIELD,
    EMAIL_VERIFICATION_ROUTES,
    OAUTH_MODULE_PREFIX,
    OAUTH_NAME_FIELD,
    OAUTH_PROVIDERS,
    OAUTH_STATE_TTL_SECONDS,
    OAUTH_TABLE,
    PASSWORD_RESET_ROUTES,
    REFRESH_TOKEN_TABLE,
    REFRESH_TOKEN_TTL_SECONDS,
)
from semarc.generator.utils.inflector import pluralize, resource_path, snake_case


PARAM_PATTERN = re.compile(r"^\{([a-z][a-z0-9_]*)\}$")
TOKEN_TTL_SECONDS = 3600
AUTH_RATE_LIMIT = {"attempts": 10, "window_seconds": 60}

COLLECTION_OPERATIONS = {"GET": "list", "POST": "create"}
ITEM_OPERATIONS = {"GET": "read", "PUT": "replace", "PATCH": "update", "DELETE": "delete"}
OWNER_ONLY_KINDS = {"replace", "update", "delete"}
ROLES_MODULE = "auth.roles"
DEFAULT_ROLE = "user"
ADMIN_ROLE = "admin"
ROLE_ROUTE = ("PUT", "/users/{id}/role")


class ResourcePlanner:
    """Plans model specs, auth identity and route operations from semantic intent.

    The planner is target-neutral: it decides what each endpoint means, which
    fields are writable, and which routes need an authenticated caller.
    """

    def plan(self, architecture, foreign_keys: list[dict]) -> dict:
        auth = self._auth(architecture)
        models = self._model_specs(architecture, auth, foreign_keys)
        routes = self._routes(architecture, auth, models)
        return {
            "auth": auth,
            "models": models,
            "routes": routes,
            "internal_tables": self._internal_tables(auth),
        }

    def _internal_tables(self, auth: dict | None) -> list[dict]:
        """Tables owned by generated infrastructure rather than declared models."""
        if not auth:
            return []
        users = self._table_name(auth["model"])
        tables = [
            self._token_table(auth["features"][feature]["table"], users)
            for feature in ["password_reset", "email_verification"]
            if auth["features"][feature]
        ]
        oauth = auth["features"]["oauth"]
        if oauth:
            tables.append(
                {
                    "model": None,
                    "table": oauth["table"],
                    "internal": True,
                    "fields": [
                        {"name": "provider", "type": "STRING", "required": True, "unique": False},
                        {"name": "provider_subject", "type": "STRING", "required": True, "unique": True},
                    ],
                    "foreign_keys": [
                        {
                            "table": oauth["table"],
                            "column": "user_id",
                            "references_table": users,
                            "references_column": "id",
                            "unique": False,
                            "on_delete": "CASCADE",
                        }
                    ],
                }
            )
        refresh = auth["features"]["refresh_tokens"]
        if refresh:
            tables.append(self._credential_table(refresh["table"], users, ["token_hash"]))
        sessions = auth["features"]["sessions"]
        if sessions:
            tables.append(self._credential_table(sessions["table"], users, ["token_hash", "csrf_hash"]))
        return tables

    def _credential_table(self, table: str, users: str, hashes: list[str]) -> dict:
        """Revocable, expiring credentials (refresh tokens, sessions) stored as hashes."""
        return {
            "model": None,
            "table": table,
            "internal": True,
            "fields": [
                *({"name": name, "type": "STRING", "required": True, "unique": name == "token_hash"} for name in hashes),
                {"name": "expires_at", "type": "DATETIME", "required": True, "unique": False},
                {"name": "revoked_at", "type": "DATETIME", "required": False, "unique": False},
            ],
            "foreign_keys": [
                {
                    "table": table,
                    "column": "user_id",
                    "references_table": users,
                    "references_column": "id",
                    "unique": False,
                    "on_delete": "CASCADE",
                }
            ],
        }

    def _auth(self, architecture) -> dict | None:
        if architecture.auth is None or architecture.auth.strategy not in ACCOUNT_STRATEGIES:
            return None
        strategy = architecture.auth.strategy
        declared = any(model.name == AUTH_MODEL for model in architecture.models)
        return {
            "strategy": strategy,
            "model": AUTH_MODEL,
            "identity_field": AUTH_IDENTITY_FIELD,
            "secret_field": AUTH_SECRET_FIELD,
            "token_ttl_seconds": TOKEN_TTL_SECONDS,
            "rate_limit": dict(AUTH_RATE_LIMIT),
            "implicit_model": not declared,
            "features": {
                "roles": self._roles(architecture),
                "refresh_tokens": (
                    {"table": REFRESH_TOKEN_TABLE, "ttl_seconds": REFRESH_TOKEN_TTL_SECONDS} if strategy == "JWT" else None
                ),
                "sessions": (
                    {
                        "table": SESSION_TABLE,
                        "ttl_seconds": SESSION_TTL_SECONDS,
                        "cookie": SESSION_COOKIE,
                        "csrf_cookie": CSRF_COOKIE,
                        "csrf_header": CSRF_HEADER,
                    }
                    if strategy == "SESSION"
                    else None
                ),
                "password_reset": (
                    {"table": "password_resets", "ttl_seconds": 3600} if self._uses(architecture, "auth.password_reset") else None
                ),
                "email_verification": (
                    {"table": "email_verifications", "ttl_seconds": 86400, "field": "email_verified_at"}
                    if self._uses(architecture, "auth.email_verification")
                    else None
                ),
                "oauth": self._oauth(architecture),
            },
        }

    def _oauth(self, architecture) -> dict | None:
        names = sorted(
            package.name.removeprefix(OAUTH_MODULE_PREFIX)
            for package in architecture.packages
            if package.name.startswith(OAUTH_MODULE_PREFIX) and package.name.removeprefix(OAUTH_MODULE_PREFIX) in OAUTH_PROVIDERS
        )
        if not names:
            return None
        user = next((model for model in architecture.models if model.name == AUTH_MODEL), None)
        has_name = user is not None and any(
            model_field.name == OAUTH_NAME_FIELD and model_field.field_type in {"STRING", "TEXT"} for model_field in user.fields
        )
        return {
            "table": OAUTH_TABLE,
            "state_ttl_seconds": OAUTH_STATE_TTL_SECONDS,
            "name_field": OAUTH_NAME_FIELD if has_name else None,
            "providers": [
                {"name": name, "env_prefix": f"OAUTH_{name.upper()}", **OAUTH_PROVIDERS[name], "scopes": list(OAUTH_PROVIDERS[name]["scopes"])}
                for name in names
            ],
        }

    def _uses(self, architecture, module: str) -> bool:
        return any(package.name == module for package in architecture.packages)

    def _token_table(self, table: str, users: str) -> dict:
        """Single-use, expiring tokens stored as hashes (password reset, email verification)."""
        return {
            "model": None,
            "table": table,
            "internal": True,
            "fields": [
                {"name": "token_hash", "type": "STRING", "required": True, "unique": True},
                {"name": "expires_at", "type": "DATETIME", "required": True, "unique": False},
                {"name": "used_at", "type": "DATETIME", "required": False, "unique": False},
            ],
            "foreign_keys": [
                {
                    "table": table,
                    "column": "user_id",
                    "references_table": users,
                    "references_column": "id",
                    "unique": False,
                    "on_delete": "CASCADE",
                }
            ],
        }

    def _roles(self, architecture) -> dict | None:
        if not any(package.name == ROLES_MODULE for package in architecture.packages):
            return None
        names = {DEFAULT_ROLE, ADMIN_ROLE} | {role for route in architecture.routes for role in route.roles}
        return {"default": DEFAULT_ROLE, "admin": ADMIN_ROLE, "names": sorted(names)}

    def _model_specs(self, architecture, auth: dict | None, foreign_keys: list[dict]) -> list[dict]:
        declared = [
            {
                "name": model.name,
                "origin": "declared",
                "fields": [
                    {
                        "name": model_field.name,
                        "type": model_field.field_type,
                        "required": "OPTIONAL" not in model_field.modifiers,
                        "unique": "UNIQUE" in model_field.modifiers,
                        "secret": False,
                        "writable": True,
                        "default": None,
                    }
                    for model_field in model.fields
                ],
            }
            for model in architecture.models
        ]

        if auth:
            auth_spec = next((spec for spec in declared if spec["name"] == auth["model"]), None)
            if auth_spec is None:
                auth_spec = {"name": auth["model"], "origin": "auth", "fields": []}
                declared.append(auth_spec)
            self._complete_credentials(auth_spec, auth)

        for spec in declared:
            spec["table"] = self._table_name(spec["name"])
            spec["resource"] = resource_path(spec["name"])
            for spec_field in spec["fields"]:
                spec_field["rules"] = self._rules_for(spec["name"], spec_field, architecture.validations)
            spec["references"] = self._references_for(spec, foreign_keys, auth)
            spec["dependents"] = self._dependents_for(spec, foreign_keys)
            spec["query"] = self._query_for(spec)
        return declared

    def _query_for(self, spec: dict) -> dict:
        """Fields list routes may filter on (equality) and sort by."""
        visible = [spec_field for spec_field in spec["fields"] if not spec_field["secret"]]
        filters = {"id": "INTEGER"}
        filters.update({spec_field["name"]: spec_field["type"] for spec_field in visible if spec_field["type"] != "DATETIME"})
        filters.update({reference["column"]: "INTEGER" for reference in spec["references"]})
        sort = ["id"] + [spec_field["name"] for spec_field in visible]
        sort += [reference["column"] for reference in spec["references"]] + ["created_at", "updated_at"]
        return {"filters": filters, "sort": sort}

    def _complete_credentials(self, spec: dict, auth: dict) -> None:
        fields = {spec_field["name"]: spec_field for spec_field in spec["fields"]}
        for credential in [auth["identity_field"], auth["secret_field"]]:
            if credential not in fields:
                spec["fields"].append(
                    {
                        "name": credential,
                        "type": "STRING",
                        "required": True,
                        "unique": False,
                        "secret": False,
                        "writable": True,
                        "default": None,
                    }
                )
        verification = auth["features"]["email_verification"]
        if verification:
            spec["fields"].append(
                {
                    "name": verification["field"],
                    "type": "DATETIME",
                    "required": False,
                    "unique": False,
                    "secret": False,
                    "writable": False,
                    "default": None,
                }
            )
        roles = auth["features"]["roles"]
        if roles:
            spec["fields"].append(
                {
                    "name": "role",
                    "type": "STRING",
                    "required": True,
                    "unique": False,
                    "secret": False,
                    "writable": False,
                    "default": roles["default"],
                }
            )
        for spec_field in spec["fields"]:
            if spec_field["name"] == auth["identity_field"]:
                spec_field["unique"] = True
            if spec_field["name"] == auth["secret_field"]:
                spec_field["secret"] = True

    def _rules_for(self, model_name: str, spec_field: dict, validations: list) -> dict:
        rules = {"required": spec_field["required"], "not_empty": False, "email": False, "min": None, "max": None}
        for validation in validations:
            if validation.field_name != spec_field["name"]:
                continue
            if validation.model_name not in {None, model_name}:
                continue
            if "REQUIRED" in validation.rules:
                rules["not_empty"] = True
            if "EMAIL" in validation.rules:
                rules["email"] = True
            if "MIN" in validation.rules:
                rules["min"] = validation.parameters["MIN"]
            if "MAX" in validation.rules:
                rules["max"] = validation.parameters["MAX"]
        return rules

    def _references_for(self, spec: dict, foreign_keys: list[dict], auth: dict | None) -> list[dict]:
        return [
            {
                "column": foreign_key["column"],
                "model": foreign_key["source_model"],
                "table": foreign_key["references_table"],
                "unique": foreign_key.get("unique", False),
                "owner": auth is not None and foreign_key["source_model"] == auth["model"],
            }
            for foreign_key in foreign_keys
            if foreign_key["table"] == spec["table"]
        ]

    def _dependents_for(self, spec: dict, foreign_keys: list[dict]) -> list[dict]:
        return [
            {
                "model": foreign_key["target_model"],
                "table": foreign_key["table"],
                "column": foreign_key["column"],
            }
            for foreign_key in foreign_keys
            if foreign_key["references_table"] == spec["table"]
        ]

    def _routes(self, architecture, auth: dict | None, models: list[dict]) -> list[dict]:
        routes = [
            self._route(route.method, route.path, route.access, "declared", auth, models, route.roles)
            for route in architecture.routes
        ]
        existing = {(route["method"], route["path"]) for route in routes}

        for spec in models:
            if spec["origin"] == "auth":
                continue
            path = "/" + spec["resource"]
            if ("GET", path) not in existing:
                routes.append(self._route("GET", path, None, "completed", auth, models))
                existing.add(("GET", path))

        if auth:
            for method, path in self._auth_routes(auth):
                if (method, path) not in existing:
                    roles = [auth["features"]["roles"]["admin"]] if (method, path) == ROLE_ROUTE else []
                    routes.append(self._route(method, path, None, "auth", auth, models, roles))
                    existing.add((method, path))
        return routes

    def _auth_routes(self, auth: dict) -> dict:
        routes = dict(AUTH_ROUTES)
        if auth["strategy"] != "JWT":
            del routes[REFRESH_ROUTE]
        if auth["features"]["roles"]:
            routes[ROLE_ROUTE] = "set_role"
        if auth["features"]["password_reset"]:
            routes.update(PASSWORD_RESET_ROUTES)
        if auth["features"]["email_verification"]:
            routes.update(EMAIL_VERIFICATION_ROUTES)
        for provider in (auth["features"]["oauth"] or {}).get("providers", []):
            routes[("GET", f"/oauth/{provider['name']}")] = "oauth_start"
            routes[("POST", f"/oauth/{provider['name']}/callback")] = "oauth_callback"
        return routes

    def _route(
        self,
        method: str,
        path: str,
        access: str | None,
        origin: str,
        auth: dict | None,
        models: list[dict],
        roles: list[str] | None = None,
    ) -> dict:
        operation = self._operation(method, path, auth, models)
        resolved_access = "protected" if roles else self._access(method, access, operation, auth)
        if resolved_access == "protected" and operation["kind"] in OWNER_ONLY_KINDS and self._has_owner(operation, models):
            operation["owner_only"] = True
        return {
            "method": method,
            "path": path,
            "origin": origin,
            "parameters": self._parameters(path),
            "operation": operation,
            "access": resolved_access,
            "roles": list(roles or []),
        }

    def _has_owner(self, operation: dict, models: list[dict]) -> bool:
        model = next((spec for spec in models if spec["name"] == operation.get("model")), None)
        return model is not None and any(reference["owner"] for reference in model["references"])

    def _operation(self, method: str, path: str, auth: dict | None, models: list[dict]) -> dict:
        if auth and (method, path) in self._auth_routes(auth):
            operation = {"kind": "auth_" + self._auth_routes(auth)[(method, path)], "model": auth["model"]}
            if (method, path) == ROLE_ROUTE:
                operation["parameter"] = "id"
            if operation["kind"] in {"auth_oauth_start", "auth_oauth_callback"}:
                operation["provider"] = path.strip("/").split("/")[1]
            return operation

        segments = [segment for segment in path.strip("/").split("/") if segment]
        if len(segments) == 1:
            model = self._model_for_segment(segments[0], models)
            kind = COLLECTION_OPERATIONS.get(method)
            if model and kind:
                return {"kind": kind, "model": model["name"]}

        if len(segments) == 2:
            model = self._model_for_segment(segments[0], models)
            parameter = PARAM_PATTERN.match(segments[1])
            kind = ITEM_OPERATIONS.get(method)
            if model and parameter and kind:
                return {"kind": kind, "model": model["name"], "parameter": parameter.group(1)}

        if len(segments) == 3 and method == "GET":
            parent = self._model_for_segment(segments[0], models)
            parameter = PARAM_PATTERN.match(segments[1])
            child = self._model_for_segment(segments[2], models)
            if parent and parameter and child:
                reference = next(
                    (item for item in child["references"] if item["model"] == parent["name"]),
                    None,
                )
                if reference:
                    return {
                        "kind": "list_related",
                        "model": child["name"],
                        "parent_model": parent["name"],
                        "parameter": parameter.group(1),
                        "foreign_key": reference["column"],
                    }

        owner = self._model_for_segment(segments[0], models) if segments else None
        return {"kind": "custom", "model": owner["name"] if owner else None}

    def _access(self, method: str, declared: str | None, operation: dict, auth: dict | None) -> str:
        if auth is None:
            return "public"
        if operation["kind"] == "auth_logout" and auth["strategy"] == "SESSION":
            return "protected"
        if operation["kind"] in {
            "auth_register",
            "auth_login",
            "auth_refresh",
            "auth_logout",
            "auth_forgot_password",
            "auth_reset_password",
            "auth_verify_email",
            "auth_oauth_start",
            "auth_oauth_callback",
        }:
            return "public"
        if operation["kind"] in {"auth_me", "auth_change_password", "auth_resend_verification"}:
            return "protected"
        if declared:
            return declared.lower()
        if operation.get("model") == auth["model"] and operation["kind"] != "custom":
            return "protected"
        return "public" if method == "GET" else "protected"

    def _parameters(self, path: str) -> list[str]:
        return [
            match.group(1)
            for segment in path.strip("/").split("/")
            if (match := PARAM_PATTERN.match(segment))
        ]

    def _model_for_segment(self, segment: str, models: list[dict]) -> dict | None:
        normalized = segment.replace("-", "_").lower()
        for spec in models:
            snake = snake_case(spec["name"])
            if normalized in {snake, spec["resource"].replace("-", "_"), pluralize(snake)}:
                return spec
        return None

    def _table_name(self, model_name: str) -> str:
        return pluralize(snake_case(model_name))

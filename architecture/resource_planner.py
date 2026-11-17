import re

from architecture.rules.auth_rules import AUTH_IDENTITY_FIELD, AUTH_MODEL, AUTH_ROUTES, AUTH_SECRET_FIELD
from generator.utils.inflector import pluralize, resource_path, snake_case


PARAM_PATTERN = re.compile(r"^\{([a-z][a-z0-9_]*)\}$")
TOKEN_TTL_SECONDS = 3600

COLLECTION_OPERATIONS = {"GET": "list", "POST": "create"}
ITEM_OPERATIONS = {"GET": "read", "PUT": "replace", "PATCH": "update", "DELETE": "delete"}


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
        }

    def _auth(self, architecture) -> dict | None:
        if architecture.auth is None or architecture.auth.strategy != "JWT":
            return None
        declared = any(model.name == AUTH_MODEL for model in architecture.models)
        return {
            "strategy": "JWT",
            "model": AUTH_MODEL,
            "identity_field": AUTH_IDENTITY_FIELD,
            "secret_field": AUTH_SECRET_FIELD,
            "token_ttl_seconds": TOKEN_TTL_SECONDS,
            "implicit_model": not declared,
        }

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
        return declared

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
            self._route(route.method, route.path, route.access, "declared", auth, models)
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
            for method, path in AUTH_ROUTES:
                if (method, path) not in existing:
                    routes.append(self._route(method, path, None, "auth", auth, models))
                    existing.add((method, path))
        return routes

    def _route(self, method: str, path: str, access: str | None, origin: str, auth: dict | None, models: list[dict]) -> dict:
        operation = self._operation(method, path, auth, models)
        return {
            "method": method,
            "path": path,
            "origin": origin,
            "parameters": self._parameters(path),
            "operation": operation,
            "access": self._access(method, access, operation, auth),
        }

    def _operation(self, method: str, path: str, auth: dict | None, models: list[dict]) -> dict:
        if auth and (method, path) in AUTH_ROUTES:
            return {"kind": "auth_" + AUTH_ROUTES[(method, path)], "model": auth["model"]}

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
        if operation["kind"] in {"auth_register", "auth_login"}:
            return "public"
        if operation["kind"] == "auth_me":
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

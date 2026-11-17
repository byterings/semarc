import re

from ast_loader import load_semantic_nodes
from architecture.rules.auth_rules import AUTH_IDENTITY_FIELD, AUTH_MODEL, AUTH_ROUTES, AUTH_SECRET_FIELD
from generator.utils.inflector import snake_case


nodes = load_semantic_nodes()
ArchitectureNode = nodes.ArchitectureNode

MODEL_NAME_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
FIELD_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
STATIC_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
PARAM_SEGMENT_PATTERN = re.compile(r"^\{([a-z][a-z0-9_]*)\}$")
IMPLICIT_FIELDS = {"id", "created_at", "updated_at"}
RESERVED_ROUTES = {("GET", "/"), ("GET", "/health"), ("GET", "/routes")}
TEXT_TYPES = {"STRING", "TEXT"}
NUMERIC_TYPES = {"INTEGER", "FLOAT"}


class SemanticValidationError(Exception):
    pass


class SemanticValidator:
    """Validates semantic meaning after parsing and before architecture expansion."""

    SUPPORTED_DATABASES = {"MYSQL", "POSTGRESQL", "SQLITE"}
    SUPPORTED_AUTH = {"JWT", "SESSION"}
    SUPPORTED_TARGETS = {"PHP", "FASTAPI", "NESTJS"}

    def __init__(self, module_registry=None) -> None:
        self.module_registry = module_registry

    def validate(self, architecture: ArchitectureNode) -> None:
        errors = []

        if architecture.project is None:
            errors.append("[Semantic Error]\nMissing project declaration")

        if architecture.database and architecture.database.engine not in self.SUPPORTED_DATABASES:
            errors.append(
                self._error(
                    f"Unsupported database type: {architecture.database.engine}",
                    architecture.database,
                )
            )

        if architecture.auth and architecture.auth.strategy not in self.SUPPORTED_AUTH:
            errors.append(
                self._error(
                    f"Unsupported auth type: {architecture.auth.strategy}",
                    architecture.auth,
                )
            )

        if architecture.target and architecture.target.name not in self.SUPPORTED_TARGETS:
            errors.append(
                self._error(
                    self.unsupported_target_message(architecture.target.name),
                    architecture.target,
                )
            )

        self._validate_duplicate_models(architecture, errors)
        self._validate_model_definitions(architecture, errors)
        self._validate_duplicate_routes(architecture, errors)
        self._validate_route_definitions(architecture, errors)
        self._validate_relations(architecture, errors)
        self._validate_foreign_key_fields(architecture, errors)
        self._validate_auth(architecture, errors)
        self._validate_validation_rules(architecture, errors)
        self._validate_used_modules(architecture, errors)

        if errors:
            raise SemanticValidationError("\n\n".join(errors))

    def validate_target_override(self, target_override: str | None) -> None:
        if target_override and target_override.upper() not in self.SUPPORTED_TARGETS:
            raise SemanticValidationError(
                "[Semantic Error]\n" + self.unsupported_target_message(target_override.upper())
            )

    def unsupported_target_message(self, target: str) -> str:
        available = ", ".join(sorted(self.SUPPORTED_TARGETS))
        return f"Unsupported target profile: {target} (available: {available})"

    def _validate_duplicate_models(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        seen = {}
        for model in architecture.models:
            if model.name in seen:
                errors.append(self._error(f"Duplicate model: {model.name}", model))
            seen[model.name] = model

    def _validate_duplicate_routes(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        seen = {}
        for route in architecture.routes:
            key = (route.method, route.path)
            if key in seen:
                errors.append(self._error(f"Duplicate route: {route.method} {route.path}", route))
            seen[key] = route

    def _validate_relations(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        model_names = {model.name for model in architecture.models}
        seen = set()
        ownership_edges = {}

        for relation in architecture.relations:
            key = (relation.source_model, relation.relation_type, relation.target_model)
            if key in seen:
                errors.append(
                    self._error(
                        f"Duplicate relationship: {relation.source_model} {relation.relation_type} {relation.target_model}",
                        relation,
                    )
                )
            seen.add(key)

            if relation.relation_type not in {"HAS_MANY", "BELONGS_TO", "HAS_ONE"}:
                errors.append(self._error(f"Invalid relationship type: {relation.relation_type}", relation))

            if relation.source_model not in model_names:
                errors.append(self._error(f"Undefined model: {relation.source_model}", relation))
            if relation.target_model not in model_names:
                errors.append(self._error(f"Undefined model: {relation.target_model}", relation))

            if relation.source_model in model_names and relation.target_model in model_names:
                parent, child = self._ownership_edge(relation)
                ownership_edges.setdefault(parent, set()).add(child)

        cycle = self._find_cycle(ownership_edges)
        if cycle:
            errors.append("[Semantic Error]\nCircular relationship: " + " -> ".join(cycle))

    def _ownership_edge(self, relation) -> tuple[str, str]:
        if relation.relation_type == "BELONGS_TO":
            return relation.target_model, relation.source_model
        return relation.source_model, relation.target_model

    def _find_cycle(self, edges: dict[str, set[str]]) -> list[str]:
        visited = set()
        stack = []

        def visit(node: str) -> list[str]:
            if node in stack:
                return stack[stack.index(node) :] + [node]
            if node in visited:
                return []

            stack.append(node)
            for child in sorted(edges.get(node, set())):
                cycle = visit(child)
                if cycle:
                    return cycle
            stack.pop()
            visited.add(node)
            return []

        for node in sorted(edges):
            cycle = visit(node)
            if cycle:
                return cycle
        return []

    def _validate_model_definitions(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        for model in architecture.models:
            if not MODEL_NAME_PATTERN.match(model.name):
                errors.append(self._error(f"Model name must be PascalCase: {model.name}", model))

            seen_fields = set()
            for model_field in model.fields:
                if not FIELD_NAME_PATTERN.match(model_field.name):
                    errors.append(
                        self._error(f"Field name must be snake_case: {model.name}.{model_field.name}", model_field)
                    )
                if model_field.name in IMPLICIT_FIELDS:
                    errors.append(
                        self._error(
                            f"Field {model.name}.{model_field.name} is generated automatically and must not be declared",
                            model_field,
                        )
                    )
                if model_field.name in seen_fields:
                    errors.append(self._error(f"Duplicate field: {model.name}.{model_field.name}", model_field))
                seen_fields.add(model_field.name)

                if len(set(model_field.modifiers)) != len(model_field.modifiers):
                    errors.append(
                        self._error(f"Duplicate field modifier on {model.name}.{model_field.name}", model_field)
                    )

    def _validate_route_definitions(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        for route in architecture.routes:
            if (route.method, route.path) in RESERVED_ROUTES:
                errors.append(
                    self._error(f"Route {route.method} {route.path} is generated automatically and is reserved", route)
                )
                continue

            segments = route.path.strip("/").split("/") if route.path != "/" else []
            parameters = []
            for segment in segments:
                parameter = PARAM_SEGMENT_PATTERN.match(segment)
                if parameter:
                    parameters.append(parameter.group(1))
                elif not STATIC_SEGMENT_PATTERN.match(segment):
                    errors.append(self._error(f"Invalid route path segment '{segment}' in {route.path}", route))
            if len(parameters) != len(set(parameters)):
                errors.append(self._error(f"Duplicate route parameter in {route.path}", route))

            if route.access == "PROTECTED" and architecture.auth is None:
                errors.append(
                    self._error(f"Route {route.method} {route.path} is PROTECTED but no AUTH strategy is declared", route)
                )
            if route.access == "PUBLIC" and (route.method, route.path) == ("GET", "/me"):
                errors.append(self._error("Route GET /me always requires authentication", route))

    def _validate_foreign_key_fields(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        models = {model.name: model for model in architecture.models}
        for relation in architecture.relations:
            parent, child = self._ownership_edge(relation)
            if parent not in models or child not in models:
                continue
            column = f"{snake_case(parent)}_id"
            for model_field in models[child].fields:
                if model_field.name == column:
                    errors.append(
                        self._error(
                            f"Field {child}.{column} conflicts with the foreign key generated by "
                            f"RELATION {relation.source_model} {relation.relation_type} {relation.target_model}",
                            model_field,
                        )
                    )

    def _validate_auth(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        strategies = architecture.metadata.get("auth_strategies", [])
        if architecture.auth and architecture.auth.strategy == "SESSION" and "JWT" not in strategies:
            errors.append(
                self._error("AUTH SESSION is not implemented by any target yet; use AUTH JWT", architecture.auth)
            )

        if architecture.auth is None or architecture.auth.strategy != "JWT":
            for route in architecture.routes:
                if (route.method, route.path) in AUTH_ROUTES and (route.method, route.path) != ("POST", "/login"):
                    errors.append(
                        self._error(f"Route {route.method} {route.path} requires AUTH JWT", route)
                    )
            return

        auth_model = next((model for model in architecture.models if model.name == AUTH_MODEL), None)
        if auth_model is None:
            return

        fields = {model_field.name: model_field for model_field in auth_model.fields}
        for credential in [AUTH_IDENTITY_FIELD, AUTH_SECRET_FIELD]:
            credential_field = fields.get(credential)
            if credential_field is None:
                continue
            if credential_field.field_type != "STRING" or "OPTIONAL" in credential_field.modifiers:
                errors.append(
                    self._error(
                        f"AUTH JWT requires {AUTH_MODEL}.{credential} to be a required STRING field",
                        credential_field,
                    )
                )

    def _validate_validation_rules(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        models = {model.name: model for model in architecture.models}
        auth_jwt = architecture.auth is not None and architecture.auth.strategy == "JWT"
        credential_fields = {AUTH_IDENTITY_FIELD: "STRING", AUTH_SECRET_FIELD: "STRING"} if auth_jwt else {}
        seen = set()

        for validation in architecture.validations:
            key = (validation.model_name, validation.field_name)
            if key in seen:
                label = f"{validation.model_name}.{validation.field_name}" if validation.model_name else validation.field_name
                errors.append(self._error(f"Duplicate validation for {label}", validation))
            seen.add(key)

            targets = self._validation_targets(validation, models, credential_fields, errors)
            for owner, field_type, modifiers in targets:
                self._validate_rules_for_field(validation, owner, field_type, modifiers, errors)

            minimum = validation.parameters.get("MIN")
            maximum = validation.parameters.get("MAX")
            if minimum is not None and maximum is not None and minimum > maximum:
                errors.append(
                    self._error(f"Validation MIN {minimum} is greater than MAX {maximum} for {validation.field_name}", validation)
                )

    def _validation_targets(self, validation, models: dict, credential_fields: dict, errors: list[str]) -> list[tuple]:
        if validation.model_name is not None:
            model = models.get(validation.model_name)
            if model is None:
                if validation.model_name == AUTH_MODEL and validation.field_name in credential_fields:
                    return [(f"{AUTH_MODEL}.{validation.field_name}", credential_fields[validation.field_name], [])]
                errors.append(self._error(f"Undefined model in validation: {validation.model_name}", validation))
                return []
            for model_field in model.fields:
                if model_field.name == validation.field_name:
                    return [(f"{model.name}.{model_field.name}", model_field.field_type, model_field.modifiers)]
            errors.append(
                self._error(f"Undefined field in validation: {validation.model_name}.{validation.field_name}", validation)
            )
            return []

        targets = [
            (f"{model.name}.{model_field.name}", model_field.field_type, model_field.modifiers)
            for model in models.values()
            for model_field in model.fields
            if model_field.name == validation.field_name
        ]
        if not targets and validation.field_name in credential_fields:
            targets.append((validation.field_name, credential_fields[validation.field_name], []))
        if not targets:
            errors.append(
                self._error(f"Validation field is not declared on any model: {validation.field_name}", validation)
            )
        return targets

    def _validate_rules_for_field(self, validation, owner: str, field_type: str, modifiers: list[str], errors: list[str]) -> None:
        for rule in validation.rules:
            if rule == "EMAIL" and field_type not in TEXT_TYPES:
                errors.append(self._error(f"EMAIL validation requires a STRING or TEXT field: {owner}", validation))
            if rule in {"MIN", "MAX"} and field_type not in TEXT_TYPES | NUMERIC_TYPES:
                errors.append(self._error(f"{rule} validation requires a text or numeric field: {owner}", validation))
            if rule == "REQUIRED" and "OPTIONAL" in modifiers:
                errors.append(self._error(f"REQUIRED validation conflicts with OPTIONAL field: {owner}", validation))

    def _validate_used_modules(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        if self.module_registry is None:
            return

        seen_modules = set()
        for package in architecture.packages:
            module = self.module_registry.get(package.name)
            if module is None:
                continue

            module_key = module.name.lower()
            if module_key in seen_modules:
                errors.append(self._error(f"SEM5002 Duplicate module usage: {module.name}", package))
            seen_modules.add(module_key)

    def _error(self, message: str, node) -> str:
        return "\n".join(
            [
                "[Semantic Error]",
                message,
                f"Line: {node.location.line}",
            ]
        )

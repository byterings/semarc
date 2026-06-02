from ast_loader import load_semantic_nodes


nodes = load_semantic_nodes()
ArchitectureNode = nodes.ArchitectureNode


class SemanticValidationError(Exception):
    pass


class SemanticValidator:
    """Validates semantic meaning after parsing and before architecture expansion."""

    SUPPORTED_DATABASES = {"MYSQL", "POSTGRESQL", "SQLITE"}
    SUPPORTED_AUTH = {"JWT", "SESSION"}
    SUPPORTED_TARGETS = {"PHP", "FASTAPI", "LARAVEL", "NODE", "NESTJS"}

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
                    f"Unsupported target profile: {architecture.target.name}",
                    architecture.target,
                )
            )

        self._validate_duplicate_models(architecture, errors)
        self._validate_duplicate_routes(architecture, errors)
        self._validate_relations(architecture, errors)
        self._validate_validation_rules(architecture, errors)
        self._validate_used_modules(architecture, errors)

        if errors:
            raise SemanticValidationError("\n\n".join(errors))

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

    def _validate_validation_rules(self, architecture: ArchitectureNode, errors: list[str]) -> None:
        valid_rules = {"REQUIRED", "EMAIL", "MIN"}
        for validation in architecture.validations:
            for rule in validation.rules:
                if rule not in valid_rules:
                    errors.append(self._error(f"Unsupported validation rule: {rule}", validation))

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

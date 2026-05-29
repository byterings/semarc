TARGET_LEAKAGE_MARKERS = {
    "php",
    "<?php",
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "APIRouter",
    "Column(",
    "ForeignKey(",
    "::class",
    "$this",
}


class CompilerContractError(Exception):
    pass


class ContractValidator:
    """Validates architecture contracts between compiler stages."""

    REQUIRED_IR_KEYS = {
        "project",
        "target",
        "target_profile",
        "config",
        "controllers",
        "services",
        "models",
        "middlewares",
        "repositories",
        "validators",
        "relationships",
        "foreign_keys",
        "migrations",
        "routes",
        "dependency_graph",
        "relationship_graph",
    }

    def validate_ast(self, ast) -> list[str]:
        errors = []
        if ast.project is None:
            errors.append("AST missing project node")
        if not isinstance(ast.models, list):
            errors.append("AST models must be a list")
        if not isinstance(ast.routes, list):
            errors.append("AST routes must be a list")
        if not isinstance(ast.relations, list):
            errors.append("AST relations must be a list")
        return errors

    def validate_ir(self, ir: dict) -> list[str]:
        errors = []
        missing = sorted(self.REQUIRED_IR_KEYS - set(ir))
        if missing:
            errors.append(f"IR missing required keys: {', '.join(missing)}")

        for model in ir.get("models", []):
            errors.extend(self._validate_model(model))
        for route in ir.get("routes", []):
            errors.extend(self._validate_route(route))
        for repository in ir.get("repositories", []):
            errors.extend(self._validate_repository(repository))

        leakage = self.detect_target_leakage(ir)
        if leakage:
            errors.append("IR target leakage detected: " + ", ".join(leakage))

        return errors

    def validate_generator_result(self, generated_components: list[dict[str, str]]) -> list[str]:
        errors = []
        for component in generated_components:
            if "created" not in component or "template" not in component:
                errors.append(f"Malformed generated component entry: {component}")
        return errors

    def detect_target_leakage(self, value) -> list[str]:
        found = set()
        self._scan(value, found)
        return sorted(found)

    def assert_valid(self, label: str, errors: list[str]) -> None:
        if errors:
            raise CompilerContractError(f"{label} contract failed:\n" + "\n".join(errors))

    def _validate_model(self, model: dict) -> list[str]:
        errors = []
        for key in ["name", "fields", "relations", "foreign_keys"]:
            if key not in model:
                errors.append(f"Model IR missing {key}: {model}")
        return errors

    def _validate_route(self, route: dict) -> list[str]:
        errors = []
        for key in ["method", "path", "handler"]:
            if key not in route:
                errors.append(f"Route IR missing {key}: {route}")

        handler = route.get("handler", {})
        if handler.get("type") == "controller":
            for key in ["component", "action"]:
                if key not in handler:
                    errors.append(f"Controller handler missing {key}: {handler}")
        return errors

    def _validate_repository(self, repository: dict) -> list[str]:
        errors = []
        for key in ["name", "model", "type", "dependencies"]:
            if key not in repository:
                errors.append(f"Repository IR missing {key}: {repository}")
        return errors

    def _scan(self, value, found: set[str]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"target", "target_profile"}:
                    continue
                self._scan(item, found)
        elif isinstance(value, list):
            for item in value:
                self._scan(item, found)
        elif isinstance(value, str):
            for marker in TARGET_LEAKAGE_MARKERS:
                if marker in value:
                    found.add(marker)

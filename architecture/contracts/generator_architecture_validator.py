from pathlib import Path

from architecture.contracts.contract_error import ContractError
from generator.utils.inflector import pluralize


class GeneratorArchitectureValidator:
    """Checks generated artifacts against the generation contract."""

    DISALLOWED_DUPLICATE_TREES = {
        "php": ["app/Controllers", "app/Services", "app/Models"],
        "fastapi": ["app/routers", "app/services", "app/models", "app/repositories"],
        "nestjs": [],
    }

    def validate(self, contract, target_definition, output_dir: str, generated_components: list[dict]) -> None:
        errors = []
        errors.extend(self._duplicate_output_paths(generated_components))
        errors.extend(self._missing_artifacts(contract, target_definition, output_dir))
        errors.extend(self._dead_duplicate_trees(target_definition, output_dir))
        errors.extend(self._broken_php_requires(target_definition, output_dir))
        errors.extend(self._missing_experience_endpoints(target_definition, output_dir))
        errors.extend(self._orphan_artifacts(contract, target_definition, output_dir))

        if errors:
            raise ContractError("\n".join(f"- {error}" for error in errors), code="SEMGEN002")

    def _duplicate_output_paths(self, generated_components: list[dict]) -> list[str]:
        paths = [component["created"] for component in generated_components]
        duplicates = sorted({path for path in paths if paths.count(path) > 1})
        return [f"Duplicate generated output path: {path}" for path in duplicates]

    def _missing_artifacts(self, contract, target_definition, output_dir: str) -> list[str]:
        target = target_definition.generator
        root = Path(output_dir)
        expected = []
        for component in contract.components.values():
            model = component.metadata.get("model")
            if target == "php":
                if component.layer == "entity" and model:
                    expected.append(root / "models" / f"{model}.php")
                if component.layer == "persistence" and model:
                    expected.append(root / "repositories" / f"{model}Repository.php")
                if component.layer == "business" and model:
                    expected.append(root / "services" / f"{model}Service.php")
                if component.layer == "api" and model:
                    expected.append(root / "controllers" / f"{model}Controller.php")
            elif target == "fastapi":
                snake = self._snake_case(model) if model else ""
                if component.layer == "entity" and model:
                    expected.append(root / "models" / f"{snake}.py")
                if component.layer == "persistence" and model:
                    expected.append(root / "repositories" / f"{snake}_repository.py")
                if component.layer == "business" and model:
                    expected.append(root / "services" / f"{snake}_service.py")
                if component.layer == "api" and model:
                    expected.append(root / "routers" / f"{snake}.py")
            elif target == "nestjs" and model:
                folder = self._pluralize(self._segment_name(model))
                if component.layer == "persistence":
                    expected.append(root / "src" / "modules" / folder / f"{folder}.repository.ts")
                if component.layer == "api":
                    expected.append(root / "src" / "modules" / folder / f"{folder}.controller.ts")

        return [
            f"Missing generated artifact for contract: {path.relative_to(root)}"
            for path in expected
            if not path.exists()
        ]

    def _dead_duplicate_trees(self, target_definition, output_dir: str) -> list[str]:
        root = Path(output_dir)
        errors = []
        for relative_path in self.DISALLOWED_DUPLICATE_TREES.get(target_definition.generator, []):
            if (root / relative_path).exists():
                errors.append(f"Duplicate generated architecture tree exists: {relative_path}")
        return errors

    def _broken_php_requires(self, target_definition, output_dir: str) -> list[str]:
        if target_definition.generator != "php":
            return []
        root = Path(output_dir)
        errors = []
        for path in sorted(root.rglob("*.php")):
            for line in path.read_text(encoding="utf-8").splitlines():
                target = self._extract_require_target(line)
                if target is None:
                    continue
                resolved = (path.parent / target).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    continue
                if not resolved.exists():
                    errors.append(f"Broken PHP require in {path.relative_to(root)}: {target}")
        return errors

    def _missing_experience_endpoints(self, target_definition, output_dir: str) -> list[str]:
        root = Path(output_dir)
        target = target_definition.generator
        checks = {
            "php": root / "routes.php",
            "fastapi": root / "main.py",
            "nestjs": root / "src" / "app.controller.ts",
        }
        path = checks.get(target)
        if path is None or not path.exists():
            return [f"Missing project experience endpoint file for target: {target}"]
        content = path.read_text(encoding="utf-8")
        required = {
            "php": ["$router->add('GET', '/',", "$router->add('GET', '/health',", "$router->add('GET', '/routes',"],
            "fastapi": ['@app.get("/",', '@app.get("/health")', '@app.get("/routes")'],
            "nestjs": ["@Get()", "@Get('health')", "@Get('routes')"],
        }[target]
        return [
            f"Missing generated project endpoint marker: {marker}"
            for marker in required
            if marker not in content
        ]

    def _orphan_artifacts(self, contract, target_definition, output_dir: str) -> list[str]:
        target = target_definition.generator
        if target == "php":
            return self._php_orphans(contract, output_dir)
        if target == "fastapi":
            return self._fastapi_orphans(contract, output_dir)
        if target == "nestjs":
            return self._nestjs_orphans(contract, output_dir)
        return []

    def _php_orphans(self, contract, output_dir: str) -> list[str]:
        root = Path(output_dir)
        routes = (root / "routes.php").read_text(encoding="utf-8") if (root / "routes.php").exists() else ""
        errors = []
        for component in contract.components.values():
            model = component.metadata.get("model")
            if not model:
                continue
            if component.layer == "api" and f"new {model}Controller()" not in routes:
                errors.append(f"Unreachable PHP controller for model route: {model}Controller")
            service_path = root / "services" / f"{model}Service.php"
            controller_path = root / "controllers" / f"{model}Controller.php"
            repository_path = root / "repositories" / f"{model}Repository.php"
            if service_path.exists() and controller_path.exists():
                if f"new {model}Service()" not in controller_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused PHP service: {model}Service")
            if repository_path.exists() and service_path.exists():
                if f"new {model}Repository()" not in service_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused PHP repository: {model}Repository")
        return errors

    def _fastapi_orphans(self, contract, output_dir: str) -> list[str]:
        root = Path(output_dir)
        main = (root / "main.py").read_text(encoding="utf-8") if (root / "main.py").exists() else ""
        errors = []
        for component in contract.components.values():
            model = component.metadata.get("model")
            if not model:
                continue
            snake = self._snake_case(model)
            if component.layer == "api" and f"from routers.{snake} import router as {snake}_router" not in main:
                errors.append(f"Unreachable FastAPI router: {snake}")
            service_path = root / "services" / f"{snake}_service.py"
            router_path = root / "routers" / f"{snake}.py"
            repository_path = root / "repositories" / f"{snake}_repository.py"
            if router_path.exists() and service_path.exists():
                if f"{model}Service" not in router_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused FastAPI service: {model}Service")
            if repository_path.exists() and service_path.exists():
                if f"{model}Repository" not in service_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused FastAPI repository: {model}Repository")
        return errors

    def _nestjs_orphans(self, contract, output_dir: str) -> list[str]:
        root = Path(output_dir)
        app_module = (root / "src" / "app.module.ts").read_text(encoding="utf-8") if (root / "src" / "app.module.ts").exists() else ""
        errors = []
        for component in contract.components.values():
            model = component.metadata.get("model")
            if not model:
                continue
            folder = self._pluralize(self._segment_name(model))
            module_name = f"{model}Module"
            if component.layer == "api" and module_name not in app_module:
                errors.append(f"Unreachable NestJS module: {module_name}")
            module_dir = root / "src" / "modules" / folder
            service_path = module_dir / f"{folder}.service.ts"
            controller_path = module_dir / f"{folder}.controller.ts"
            repository_path = module_dir / f"{folder}.repository.ts"
            if controller_path.exists() and service_path.exists():
                if f"{model}Service" not in controller_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused NestJS service: {model}Service")
            if repository_path.exists() and service_path.exists():
                if f"{model}Repository" not in service_path.read_text(encoding="utf-8"):
                    errors.append(f"Unused NestJS repository: {model}Repository")
        return errors

    def _extract_require_target(self, line: str) -> str | None:
        marker = "require_once __DIR__ . '"
        if marker not in line:
            return None
        remainder = line.split(marker, 1)[1]
        target = remainder.split("'", 1)[0]
        return target[1:] if target.startswith("/") else target

    def _snake_case(self, value: str) -> str:
        output = []
        for index, char in enumerate(value):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output)

    def _segment_name(self, value: str) -> str:
        return self._snake_case(value).replace("_", "-")

    def _pluralize(self, value: str) -> str:
        return pluralize(value)

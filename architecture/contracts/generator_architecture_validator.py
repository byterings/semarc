from pathlib import Path

from architecture.contracts.contract_error import ContractError


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
            elif target == "fastapi":
                snake = self._snake_case(model) if model else ""
                if component.layer == "entity" and model:
                    expected.append(root / "models" / f"{snake}.py")
                if component.layer == "persistence" and model:
                    expected.append(root / "repositories" / f"{snake}_repository.py")
                if component.layer == "business" and model:
                    expected.append(root / "services" / f"{snake}_service.py")
            elif target == "nestjs" and model:
                folder = self._pluralize(self._segment_name(model))
                if component.layer == "persistence":
                    expected.append(root / "src" / "modules" / folder / f"{folder}.repository.ts")

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
        if value.endswith("y"):
            return value[:-1] + "ies"
        if value.endswith("s"):
            return value
        return value + "s"

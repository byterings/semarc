from pathlib import Path
import shutil

from generator.fastapi.mappers.config_mapper import ConfigMapper
from generator.fastapi.mappers.controller_mapper import ControllerMapper
from generator.fastapi.mappers.middleware_mapper import MiddlewareMapper
from generator.fastapi.mappers.migration_mapper import MigrationMapper
from generator.fastapi.mappers.model_mapper import ModelMapper
from generator.fastapi.mappers.repository_mapper import RepositoryMapper
from generator.fastapi.mappers.service_mapper import ServiceMapper
from generator.php.template_engine import TemplateEngine


class FastApiGenerator:
    """Generates an idiomatic FastAPI backend from language-neutral IR."""

    def __init__(self, output_dir: str = "output", debug: bool = False) -> None:
        self.output_dir = Path(output_dir)
        self.template_engine = TemplateEngine(template_dir="templates/fastapi")
        self.debug = debug
        self.generated_components: list[dict[str, str]] = []
        self.mapper_selections: list[dict[str, str]] = []

    def generate(self, ir: dict) -> None:
        self.generated_components = []
        self.mapper_selections = []
        self._prepare_output_dirs()

        self._write_mapped(ConfigMapper().map(ir), "ConfigMapper")
        self._write_mapped(ModelMapper().map(ir), "ModelMapper")
        self._write_mapped(ServiceMapper().map(ir), "ServiceMapper")
        self._write_mapped(MiddlewareMapper().map(ir), "MiddlewareMapper")
        self._write_mapped(ControllerMapper().map(ir), "ControllerMapper")
        self._write_mapped(RepositoryMapper().map(ir), "RepositoryMapper")
        self._write_mapped(MigrationMapper().map(ir), "MigrationMapper")
        self._write_main(ir)
        self._write_init_files()

        if self.debug:
            print("\n[FastAPI Mappers]")
            for selection in self.mapper_selections:
                print(f"Mapper: {selection['mapper']}")
                print(f"Output: {selection['output']}")
                print(f"Template: {selection['template']}")
            print("\n[Generator]")
            for component in self.generated_components:
                print(f"Created: {component['created']}")
                print(f"Template: {component['template']}")

    def _prepare_output_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for legacy_file in ["routes.php"]:
            path = self.output_dir / legacy_file
            if path.exists():
                path.unlink()

        for cache_dir in self.output_dir.rglob("__pycache__"):
            shutil.rmtree(cache_dir)

        for directory in [
            "config",
            "routers",
            "services",
            "middleware",
            "models",
            "schemas",
            "repositories",
            "migrations",
        ]:
            target = self.output_dir / directory
            target.mkdir(parents=True, exist_ok=True)
            for generated_file in target.glob("*"):
                if generated_file.is_file() and generated_file.suffix in {".py", ".php", ".sql"}:
                    generated_file.unlink()

        for unused in ["routes", "controllers", "validators"]:
            self._remove_generated_directory(unused)

    def _write_main(self, ir: dict) -> None:
        self._write(
            self.output_dir / "main.py",
            "main.tpl",
            {"project_name": ir["project"]},
        )

    def _write_mapped(self, mappings: list[dict], mapper_name: str) -> None:
        for mapping in mappings:
            path = self.output_dir / mapping["path"]
            self._write(path, mapping["template"], mapping["values"])
            self.mapper_selections.append(
                {
                    "mapper": mapper_name,
                    "output": mapping["path"],
                    "template": mapping["template"],
                }
            )

    def _write(self, path: Path, template: str, values: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.template_engine.render(template, values), encoding="utf-8")
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

    def _write_init_files(self) -> None:
        for directory in [
            "config",
            "routers",
            "services",
            "middleware",
            "models",
            "schemas",
            "repositories",
            "migrations",
        ]:
            (self.output_dir / directory / "__init__.py").write_text("", encoding="utf-8")

    def _remove_generated_directory(self, directory: str) -> None:
        target = self.output_dir / directory
        if not target.exists():
            return
        for generated_file in target.glob("*"):
            if generated_file.is_file() and generated_file.suffix in {".py", ".php", ".sql"}:
                generated_file.unlink()
        try:
            target.rmdir()
        except OSError:
            pass

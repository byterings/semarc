from pathlib import Path
import shutil

from generator.project_files import ProjectFileWriter
from generator.fastapi.mappers.config_mapper import ConfigMapper
from generator.fastapi.mappers.controller_mapper import ControllerMapper
from generator.fastapi.mappers.middleware_mapper import MiddlewareMapper
from generator.fastapi.mappers.migration_mapper import MigrationMapper
from generator.fastapi.mappers.model_mapper import ModelMapper
from generator.fastapi.mappers.repository_mapper import RepositoryMapper
from generator.fastapi.mappers.service_mapper import ServiceMapper
from generator.php.template_engine import TemplateEngine
from generator.utils.project_experience import SEMARC_VERSION, complete_routes, model_names, module_names, profile_names, route_lines


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
        self._generate_project_template(ir)

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
        nestjs_src = self.output_dir / "src"
        if nestjs_src.exists():
            shutil.rmtree(nestjs_src)

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

        for unused in ["routes", "controllers", "validators", "app"]:
            self._remove_generated_directory(unused)

    def _write_main(self, ir: dict) -> None:
        routers = self._router_modules(ir)
        self._write(
            self.output_dir / "main.py",
            "main.tpl",
            {
                "project_name": ir["project"],
                "semarc_version": SEMARC_VERSION,
                "models": repr(model_names(ir)),
                "routes": repr(["GET /", "GET /health", "GET /routes"] + route_lines(ir)),
                "profiles": repr(profile_names(ir)),
                "modules": repr(module_names(ir)),
                "router_imports": "\n".join(
                    f"from routers.{module} import router as {module}_router"
                    for module in routers
                ),
                "router_includes": "\n".join(
                    f"app.include_router({module}_router)"
                    for module in routers
                ),
            },
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
            (self.output_dir / directory / "__init__.py").write_text(
                "# Generated package marker.\n",
                encoding="utf-8",
            )

    def _generate_project_template(self, ir: dict) -> None:
        writer = ProjectFileWriter(self.output_dir, self._record_project_file)
        for directory in [
            "tests",
        ]:
            (self.output_dir / directory).mkdir(parents=True, exist_ok=True)

        writer.write_text(
            "tests/test_app.py",
            "\n".join(
                [
                    "from pathlib import Path",
                    "",
                    "",
                    "def test_generated_routes_are_documented():",
                    f"    expected_routes = {repr(['GET /', 'GET /health', 'GET /routes'] + route_lines(ir))}",
                    "    assert 'GET /health' in expected_routes",
                    "",
                    "",
                    "def test_generated_layers_exist():",
                    "    root = Path(__file__).resolve().parents[1]",
                    "    assert (root / 'routers').is_dir()",
                    "    assert (root / 'services').is_dir()",
                    "    assert (root / 'repositories').is_dir()",
                    "    assert (root / 'models').is_dir()",
                    "",
                ]
            ),
            "fastapi scaffold tests",
        )
        writer.write_text(
            "requirements.txt",
            "fastapi\nuvicorn\nsqlalchemy\n",
            "fastapi requirements",
        )
        writer.write_readme(ir, "fastapi")
        writer.write_env_example(
            ir,
            {
                "APP_NAME": ir["project"],
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "3306",
                "DB_DATABASE": "semarc_app",
            },
        )
        writer.write_text(
            "Dockerfile",
            "\n".join(
                [
                    "FROM python:3.12-slim",
                    "WORKDIR /app",
                    "COPY requirements.txt .",
                    "RUN pip install --no-cache-dir -r requirements.txt",
                    "COPY . .",
                    "EXPOSE 8000",
                    "CMD [\"uvicorn\", \"main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]",
                    "",
                ]
            ),
            "fastapi Dockerfile",
        )
        writer.write_text(
            "docker-compose.yml",
            "\n".join(
                [
                    "services:",
                    "  app:",
                    "    build: .",
                    "    ports:",
                    "      - \"8000:8000\"",
                    "",
                ]
            ),
            "fastapi docker compose",
        )
        writer.write_manifest(ir, "fastapi")

    def _record_project_file(self, path: Path, template: str) -> None:
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

    def _copy_tree_files(self, source_dir: str, destination_dir: str, suffix: str) -> None:
        source = self.output_dir / source_dir
        destination = self.output_dir / destination_dir
        if not source.exists():
            return
        destination.mkdir(parents=True, exist_ok=True)
        for path in sorted(source.glob(f"*{suffix}")):
            target = destination / path.name
            if target.exists():
                continue
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            self.generated_components.append(
                {
                    "created": str(target.relative_to(self.output_dir)),
                    "template": "project file copy",
                }
            )

    def _remove_generated_directory(self, directory: str) -> None:
        target = self.output_dir / directory
        if not target.exists():
            return
        if target.is_dir() and any(child.is_dir() for child in target.iterdir()):
            shutil.rmtree(target)
            return
        for generated_file in target.glob("*"):
            if generated_file.is_file() and generated_file.suffix in {".py", ".php", ".sql"}:
                generated_file.unlink()
        try:
            target.rmdir()
        except OSError:
            pass

    def _router_modules(self, ir: dict) -> list[str]:
        modules = []
        if any(route["path"] == "/login" for route in complete_routes(ir)):
            modules.append("auth")
        for model in ir["models"]:
            snake = self._snake_case(model["name"])
            if any(self._first_segment(route["path"]) in {snake, self._pluralize(snake)} for route in complete_routes(ir)):
                modules.append(snake)
        return modules

    def _first_segment(self, path: str) -> str:
        parts = [part for part in path.strip("/").split("/") if part]
        return parts[0].replace("-", "_").lower() if parts else ""

    def _snake_case(self, value: str) -> str:
        output = []
        for index, char in enumerate(value):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output)

    def _pluralize(self, value: str) -> str:
        if value.endswith("y"):
            return value[:-1] + "ies"
        if value.endswith("s"):
            return value
        return value + "s"

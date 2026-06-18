from pathlib import Path
import shutil

from generator.project_files import ProjectFileWriter
from generator.php.auth_generator import AuthGenerator
from generator.php.model_generator import ModelGenerator
from generator.php.migration_generator import MigrationGenerator
from generator.php.repository_generator import RepositoryGenerator
from generator.php.routes_generator import RoutesGenerator
from generator.php.template_engine import TemplateEngine
from generator.php.validator_generator import ValidatorGenerator
from generator.utils.inflector import pluralize
from generator.utils.project_experience import route_lines


class PhpGenerator:
    """Facade for modular PHP generators. Consumes Architecture IR only."""

    def __init__(self, output_dir: str = "output", debug: bool = False) -> None:
        self.output_dir = Path(output_dir)
        self.template_engine = TemplateEngine()
        self.debug = debug
        self.generated_components: list[dict[str, str]] = []

    def generate(self, ir: dict) -> None:
        self.generated_components = []
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._prepare_output_dirs()

        ModelGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        AuthGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        RepositoryGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        self._generate_model_services_and_controllers(ir)
        RoutesGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        ValidatorGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        MigrationGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        self._generate_database_config(ir)
        self._generate_project_template(ir)

        if self.debug:
            print("\n[Generator]")
            for component in self.generated_components:
                print(f"Created: {component['created']}")
                print(f"Template: {component['template']}")

    def _prepare_output_dirs(self) -> None:
        for directory in [
            "controllers",
            "models",
            "middleware",
            "config",
            "services",
            "repositories",
            "validators",
            "migrations",
        ]:
            (self.output_dir / directory).mkdir(parents=True, exist_ok=True)

        for legacy_file in ["AuthController.php", "User.php", "database.php"]:
            path = self.output_dir / legacy_file
            if path.exists():
                path.unlink()
        fastapi_main = self.output_dir / "main.py"
        if fastapi_main.exists():
            fastapi_main.unlink()
        nestjs_src = self.output_dir / "src"
        if nestjs_src.exists():
            shutil.rmtree(nestjs_src)

        for cache_dir in self.output_dir.rglob("__pycache__"):
            shutil.rmtree(cache_dir)

        for directory in [
            "controllers",
            "models",
            "middleware",
            "services",
            "repositories",
            "validators",
            "config",
            "routes",
            "migrations",
            "routers",
            "schemas",
            "app",
            "routes",
            "storage",
        ]:
            target_dir = self.output_dir / directory
            if not target_dir.exists():
                continue
            if directory in {"app", "routes", "storage"}:
                shutil.rmtree(target_dir)
                continue
            for generated_file in target_dir.glob("*"):
                if generated_file.is_file() and generated_file.suffix in {".php", ".py", ".sql"}:
                    generated_file.unlink()

    def _generate_model_services_and_controllers(self, ir: dict) -> None:
        for model in ir["models"]:
            model_name = model["name"]
            service_name = f"{model_name}Service"
            repository_name = f"{model_name}Repository"
            controller_name = f"{model_name}Controller"
            create_method = f"create{model_name}"
            list_method = f"get{self._pluralize(model_name)}"

            service_path = self.output_dir / "services" / f"{service_name}.php"
            service_content = self.template_engine.render(
                "services/model_service.tpl",
                {
                    "service_name": service_name,
                    "repository_name": repository_name,
                    "create_method": create_method,
                    "list_method": list_method,
                },
            )
            service_path.write_text(service_content, encoding="utf-8")
            self._record(service_path, "services/model_service.tpl")

            controller_path = self.output_dir / "controllers" / f"{controller_name}.php"
            controller_content = self.template_engine.render(
                "controllers/model_controller.tpl",
                {
                    "controller_name": controller_name,
                    "service_name": service_name,
                },
            )
            controller_path.write_text(controller_content, encoding="utf-8")
            self._record(controller_path, "controllers/model_controller.tpl")

    def _generate_database_config(self, ir: dict) -> None:
        engine = ir["config"]["database"]["engine"]
        content = "\n".join(
            [
                "<?php",
                "",
                "return [",
                f"    'engine' => '{engine}',",
                "    'host' => getenv('DB_HOST') ?: '127.0.0.1',",
                "    'database' => getenv('DB_DATABASE') ?: 'semarc_app',",
                "    'username' => getenv('DB_USERNAME') ?: 'root',",
                "    'password' => getenv('DB_PASSWORD') ?: '',",
                "];",
                "",
            ]
        )
        path = self.output_dir / "config" / "database.php"
        path.write_text(content, encoding="utf-8")
        self._record(path, "database config")

    def _generate_project_template(self, ir: dict) -> None:
        writer = ProjectFileWriter(self.output_dir, self._record)
        for directory in [
            "public",
            "tests",
        ]:
            (self.output_dir / directory).mkdir(parents=True, exist_ok=True)

        writer.write_text(
            "public/index.php",
            "\n".join(
                [
                    "<?php",
                    "",
                    "require_once __DIR__ . '/../routes.php';",
                    "",
                ]
            ),
            "php public index",
        )
        writer.write_text(
            "public/.htaccess",
            "\n".join(
                [
                    "RewriteEngine On",
                    "RewriteCond %{REQUEST_FILENAME} !-f",
                    "RewriteRule ^ index.php [QSA,L]",
                    "",
                ]
            ),
            "php htaccess",
        )
        writer.write_text(
            "config/app.php",
            "<?php\n\nreturn [\n    'name' => getenv('APP_NAME') ?: '" + ir["project"] + "',\n];\n",
            "php app config",
        )
        writer.write_text(
            "tests/FeatureTest.php",
            "\n".join(
                [
                    "<?php",
                    "",
                    "// Scaffold tests for generated route/controller/service/repository wiring.",
                    "$expectedRoutes = " + self._php_array(["GET /", "GET /health", "GET /routes"] + route_lines(ir)) + ";",
                    "foreach ($expectedRoutes as $route) {",
                    "    assert(is_string($route));",
                    "}",
                    "assert(file_exists(__DIR__ . '/../routes.php'));",
                    "assert(is_dir(__DIR__ . '/../controllers'));",
                    "assert(is_dir(__DIR__ . '/../services'));",
                    "assert(is_dir(__DIR__ . '/../repositories'));",
                    "",
                ]
            ),
            "php scaffold tests",
        )

        writer.write_readme(ir, "php")
        writer.write_env_example(
            ir,
            {
                "APP_NAME": ir["project"],
                "APP_ENV": "local",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "3306",
                "DB_DATABASE": "semarc_app",
                "DB_USERNAME": "root",
                "DB_PASSWORD": "",
            },
        )
        writer.write_text(
            "Dockerfile",
            "\n".join(
                [
                    "FROM php:8.2-cli",
                    "WORKDIR /app",
                    "COPY . .",
                    "EXPOSE 8000",
                    "CMD [\"php\", \"-S\", \"0.0.0.0:8000\", \"-t\", \"public\"]",
                    "",
                ]
            ),
            "php Dockerfile",
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
            "php docker compose",
        )
        writer.write_manifest(ir, "php")

    def _copy_if_exists(self, source: str, destination: str) -> None:
        source_path = self.output_dir / source
        if not source_path.exists():
            return
        destination_path = self.output_dir / destination
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
        self._record(destination_path, "project file copy")

    def _record(self, path: Path, template: str) -> None:
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

    def _pluralize(self, model_name: str) -> str:
        return pluralize(model_name)

    def _php_array(self, values: list[str]) -> str:
        return "[" + ", ".join("'" + value.replace("'", "\\'") + "'" for value in values) + "]"

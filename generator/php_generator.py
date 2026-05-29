from pathlib import Path
import shutil

from generator.php.auth_generator import AuthGenerator
from generator.php.model_generator import ModelGenerator
from generator.php.migration_generator import MigrationGenerator
from generator.php.repository_generator import RepositoryGenerator
from generator.php.routes_generator import RoutesGenerator
from generator.php.template_engine import TemplateEngine
from generator.php.validator_generator import ValidatorGenerator


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

        RoutesGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        ModelGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        AuthGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        RepositoryGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        ValidatorGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        MigrationGenerator(self.output_dir, self.template_engine, self._record).generate(ir)
        self._generate_database_config(ir)

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
        ]:
            target_dir = self.output_dir / directory
            if not target_dir.exists():
                continue
            for generated_file in target_dir.glob("*"):
                if generated_file.is_file() and generated_file.suffix in {".php", ".py", ".sql"}:
                    generated_file.unlink()

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

    def _record(self, path: Path, template: str) -> None:
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

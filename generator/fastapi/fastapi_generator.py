import json
from pathlib import Path

from generator.fastapi.api_code import auth_router_code, custom_router_code, main_code, model_router_code
from generator.fastapi.entity_code import model_code, module_name, repository_code, schema_code, service_code
from generator.fastapi.migration_code import migration_code, migration_file_name
from generator.project_files import ProjectFileWriter
from generator.utils.api_scenario import ApiScenarioBuilder
from generator.utils.project_runtime import database_settings, docker_compose, env_example, readme
from generator.utils.resource_views import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from generator.utils.template_engine import TemplateEngine

PORT = 8000
REQUIREMENTS = [
    "fastapi==0.163.1",
    "uvicorn[standard]==0.54.0",
    "sqlalchemy==2.1.9",
    "alembic==1.20.1",
    "pydantic==2.14.3",
    "python-dotenv==1.2.4",
    "pymysql==1.2.4",
    "cryptography==50.0.2",
    "psycopg[binary]==3.3.9",
    "pytest==9.2.0",
    "httpx2==2.16.2",
]
AUTH_REQUIREMENTS = ["pyjwt==2.15.1", "bcrypt==5.0.0"]
PACKAGES = {
    "config": "Application settings.",
    "core": "Shared application infrastructure.",
    "schemas": "Pydantic request and response models.",
    "repositories": "Database access.",
    "services": "Business rules.",
    "routers": "HTTP endpoints.",
}


class FastApiGenerator:
    """Maps Architecture IR to a runnable FastAPI + SQLAlchemy project."""

    def __init__(self, output_dir: str = "output", debug: bool = False) -> None:
        self.output_dir = Path(output_dir)
        self.template_engine = TemplateEngine("fastapi")
        self.debug = debug
        self.generated_components: list[dict[str, str]] = []

    def generate(self, ir: dict) -> None:
        self.generated_components = []
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._runtime(ir)
        routers = self._entities_and_routers(ir)
        self._migrations(ir)
        self._write("main.py", main_code(ir, routers), "fastapi main")
        self._project(ir)
        ProjectFileWriter(self.output_dir, self._record).write_manifest(ir, "fastapi")

        if self.debug:
            print("\n[Generator]")
            for component in self.generated_components:
                print(f"Created: {component['created']}")
                print(f"Template: {component['template']}")

    def _runtime(self, ir: dict) -> None:
        for package, purpose in PACKAGES.items():
            self._write(f"{package}/__init__.py", f'"""{purpose}"""\n', "python package")
        self._write("config/settings.py", self._settings(ir), "fastapi settings")
        self._render("core/errors.py", "errors.py.tpl")
        self._render("database.py", "database.py.tpl")
        self._render("schemas/base.py", "schemas_base.py.tpl")
        self._render("repositories/base.py", "repository_base.py.tpl")
        self._render("services/base.py", "service_base.py.tpl", {"default_limit": DEFAULT_PAGE_SIZE, "max_limit": MAX_PAGE_SIZE})

        auth = ir.get("auth")
        if auth:
            self._write("middleware/__init__.py", '"""Request authentication dependencies."""\n', "python package")
            self._render("services/token_service.py", "token_service.py.tpl")
            self._render("services/password_hasher.py", "password_hasher.py.tpl")
            self._render(
                "middleware/auth.py",
                "auth_dependency.py.tpl",
                {"auth_model": auth["model"], "auth_module": module_name(auth["model"])},
            )

    def _entities_and_routers(self, ir: dict) -> list[str]:
        routers = []
        custom = custom_router_code(ir)
        if custom:
            self._write("routers/custom.py", custom, "fastapi custom router")
            routers.append("custom")
        if ir.get("auth"):
            self._write("routers/auth.py", auth_router_code(ir), "fastapi auth router")
            routers.append("auth")

        model_imports = []
        for model in ir["models"]:
            module = module_name(model["name"])
            self._write(f"models/{module}.py", model_code(model), "fastapi model")
            self._write(f"schemas/{module}.py", schema_code(model), "fastapi schema")
            self._write(f"repositories/{module}_repository.py", repository_code(model), "fastapi repository")
            self._write(f"services/{module}_service.py", service_code(model, ir), "fastapi service")
            model_imports.append(f"from models.{module} import {model['name']}")
            router = model_router_code(ir, model)
            if router:
                self._write(f"routers/{module}.py", router, "fastapi router")
                routers.append(module)
        names = ", ".join(repr(model["name"]) for model in ir["models"])
        registry = "\n".join(['"""Every model, imported so Alembic sees all tables."""', *model_imports, "", f"__all__ = [{names}]", ""])
        self._write("models/__init__.py", registry, "fastapi model registry")
        return routers

    def _migrations(self, ir: dict) -> None:
        self._render("alembic.ini", "alembic.ini.tpl")
        self._render("migrations/env.py", "migrations_env.py.tpl")
        self._render("migrations/script.py.mako", "script.py.mako.tpl")
        previous = None
        for table in ir["migrations"]["tables"]:
            self._write(f"migrations/versions/{migration_file_name(table)}", migration_code(table, previous), "alembic revision")
            previous = table
        self._render("migrate.py", "migrate.py.tpl")

    def _project(self, ir: dict) -> None:
        requirements = REQUIREMENTS + (AUTH_REQUIREMENTS if ir.get("auth") else [])
        self._write("requirements.txt", "\n".join(sorted(requirements, key=str.lower)) + "\n", "requirements")
        self._write("pytest.ini", "[pytest]\npythonpath = .\ntestpaths = tests\n", "pytest config")
        self._render("tests/test_api.py", "test_api.py.tpl")
        self._write(
            "tests/api_scenario.json",
            json.dumps(ApiScenarioBuilder().build(ir), indent=2) + "\n",
            "api scenario",
        )
        self._write("storage/.gitignore", "*\n!.gitignore\n", "storage gitignore")
        self._write(".gitignore", ".env\n__pycache__/\n.pytest_cache/\n.venv/\nstorage/*.sqlite\n", "gitignore")
        self._write(".env.example", env_example(ir), "env example")
        self._render("Dockerfile", "Dockerfile.tpl")
        self._write("docker-compose.yml", docker_compose(ir, PORT), "docker compose")
        self._write(
            "README.md",
            readme(
                ir,
                "FastAPI + SQLAlchemy 2 + Alembic (Python 3.11+)",
                {
                    "local": [
                        "python3 -m venv .venv && . .venv/bin/activate",
                        "pip install -r requirements.txt",
                        "cp .env.example .env",
                        "python migrate.py",
                        f"uvicorn main:app --reload --port {PORT}",
                    ],
                    "test": ["pytest"],
                },
                [
                    "`main.py` application, error handlers and router registration",
                    "`routers/` HTTP endpoints, `services/` business rules, `repositories/` queries",
                    "`models/` SQLAlchemy tables, `schemas/` Pydantic request and response models",
                    "`migrations/` Alembic revisions applied by `python migrate.py`",
                    "Interactive API docs at `/docs`",
                ],
            ),
            "project README",
        )

    def _settings(self, ir: dict) -> str:
        settings = database_settings(ir)
        lines = [
            "import os",
            "from pathlib import Path",
            "",
            "from dotenv import load_dotenv",
            "from sqlalchemy.engine import URL",
            "",
            "BASE_DIR = Path(__file__).resolve().parents[1]",
            'load_dotenv(BASE_DIR / ".env", override=False)',
            "",
            "",
            "def env(key: str, default: str = \"\") -> str:",
            "    value = os.getenv(key)",
            "    return default if value is None or value == \"\" else value",
            "",
            "",
            "class Settings:",
            "    def __init__(self) -> None:",
            f'        self.app_name = env("APP_NAME", {ir["project"]!r})',
            '        self.app_env = env("APP_ENV", "local")',
            f'        self.db_connection = env("DB_CONNECTION", {settings["connection"]!r})',
            '        self.db_host = env("DB_HOST", "127.0.0.1")',
            f'        self.db_port = env("DB_PORT", {(settings["port"] or "3306")!r})',
            f'        self.db_database = env("DB_DATABASE", {settings["database"]!r})',
            f'        self.db_username = env("DB_USERNAME", {settings["username"]!r})',
            '        self.db_password = env("DB_PASSWORD", "")',
            '        self.cors_origins = [origin.strip() for origin in env("CORS_ORIGINS", "*").split(",") if origin.strip()]',
        ]
        if ir.get("auth"):
            lines.extend(
                [
                    '        self.jwt_secret = env("JWT_SECRET", "")',
                    f'        self.jwt_ttl = int(env("JWT_TTL", "{ir["auth"]["token_ttl_seconds"]}"))',
                ]
            )
        lines.extend(
            [
                "",
                "    @property",
                "    def database_url(self) -> URL:",
                '        if self.db_connection == "sqlite":',
                "            path = self.db_database",
                '            if path != ":memory:" and not Path(path).is_absolute():',
                "                path = str(BASE_DIR / path)",
                '                Path(path).parent.mkdir(parents=True, exist_ok=True)',
                '            return URL.create("sqlite", database=path)',
                "        drivers = {\"mysql\": \"mysql+pymysql\", \"pgsql\": \"postgresql+psycopg\"}",
                "        if self.db_connection not in drivers:",
                '            raise ValueError(f"Unsupported DB_CONNECTION: {self.db_connection} (use mysql, pgsql or sqlite)")',
                "        return URL.create(",
                "            drivers[self.db_connection],",
                "            username=self.db_username,",
                "            password=self.db_password or None,",
                "            host=self.db_host,",
                "            port=int(self.db_port),",
                "            database=self.db_database,",
                '            query={"charset": "utf8mb4"} if self.db_connection == "mysql" else {},',
                "        )",
                "",
                "",
                "settings = Settings()",
                "",
            ]
        )
        return "\n".join(lines)

    def _render(self, relative_path: str, template: str, values: dict | None = None) -> None:
        self._write(relative_path, self.template_engine.render(template, values), template)

    def _write(self, relative_path: str, content: str, template: str) -> None:
        path = self.output_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._record(path, template)

    def _record(self, path: Path, template: str) -> None:
        self.generated_components.append({"created": str(path.relative_to(self.output_dir)), "template": template})

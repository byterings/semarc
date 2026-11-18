"""Runtime settings shared by every target: environment, Docker Compose, README.

All targets read the same environment variables (DB_CONNECTION, DB_HOST, ...,
JWT_SECRET, JWT_TTL), so a generated project can be switched between MySQL,
PostgreSQL and SQLite without regenerating it.
"""
from semarc.compiler.version import SEMARC_VERSION
from semarc.generator.utils.inflector import snake_case
from semarc.generator.utils.resource_views import database_engine

DEV_JWT_SECRET = "change-me-to-a-long-random-secret-value"

DATABASES = {
    "MYSQL": {
        "connection": "mysql",
        "host": "127.0.0.1",
        "port": "3306",
        "database": "semarc_app",
        "username": "root",
        "password": "",
        "image": "mysql:8.4",
    },
    "POSTGRESQL": {
        "connection": "pgsql",
        "host": "127.0.0.1",
        "port": "5432",
        "database": "semarc_app",
        "username": "postgres",
        "password": "",
        "image": "postgres:17-alpine",
    },
    "SQLITE": {
        "connection": "sqlite",
        "host": "",
        "port": "",
        "database": "storage/database.sqlite",
        "username": "",
        "password": "",
        "image": "",
    },
}


def database_settings(ir: dict) -> dict:
    return DATABASES[database_engine(ir)]


def env_values(ir: dict) -> dict[str, str]:
    settings = database_settings(ir)
    values = {
        "APP_NAME": ir["project"],
        "APP_ENV": "local",
        "DB_CONNECTION": settings["connection"],
        "DB_HOST": settings["host"],
        "DB_PORT": settings["port"],
        "DB_DATABASE": settings["database"],
        "DB_USERNAME": settings["username"],
        "DB_PASSWORD": settings["password"],
        "CORS_ORIGINS": "*",
    }
    if ir.get("auth"):
        values["JWT_SECRET"] = DEV_JWT_SECRET
        values["JWT_TTL"] = str(ir["auth"]["token_ttl_seconds"])
        values["AUTH_RATE_LIMIT"] = str(ir["auth"]["rate_limit"]["attempts"])
        values["AUTH_RATE_WINDOW"] = str(ir["auth"]["rate_limit"]["window_seconds"])
    return values


def env_example(ir: dict) -> str:
    lines = [
        "# Copy to .env and adjust. Environment variables override this file.",
        "# DB_CONNECTION accepts mysql, pgsql or sqlite.",
        "# CORS_ORIGINS is * or a comma separated list such as https://app.example.com.",
    ]
    if ir.get("auth"):
        lines.append("# JWT_SECRET must be at least 32 characters; replace it before deploying.")
    lines.extend(f"{key}={value}" for key, value in env_values(ir).items())
    return "\n".join(lines) + "\n"


def docker_compose(ir: dict, port: int) -> str:
    engine = database_engine(ir)
    project = snake_case(ir["project"])
    settings = DATABASES[engine]
    lines = [
        "services:",
        "  app:",
        "    build: .",
        "    ports:",
        f'      - "${{APP_PORT:-{port}}}:{port}"',
        "    environment:",
        f"      APP_NAME: {ir['project']}",
        "      APP_ENV: production",
        "      CORS_ORIGINS: ${CORS_ORIGINS:-*}",
    ]

    if engine == "SQLITE":
        lines.extend(
            [
                "      DB_CONNECTION: sqlite",
                "      DB_DATABASE: storage/database.sqlite",
            ]
        )
    else:
        lines.extend(
            [
                f"      DB_CONNECTION: {settings['connection']}",
                "      DB_HOST: db",
                f'      DB_PORT: "{settings["port"]}"',
                f"      DB_DATABASE: {project}",
                f"      DB_USERNAME: {project}",
                "      DB_PASSWORD: secret",
            ]
        )
    if ir.get("auth"):
        lines.append(f"      JWT_SECRET: ${{JWT_SECRET:-{DEV_JWT_SECRET}}}")

    if engine == "SQLITE":
        lines.extend(["    volumes:", "      - app-storage:/app/storage", "", "volumes:", "  app-storage:", ""])
        return "\n".join(lines)

    lines.extend(["    depends_on:", "      db:", "        condition: service_healthy", "", "  db:", f"    image: {settings['image']}"])
    if engine == "MYSQL":
        lines.extend(
            [
                "    environment:",
                f"      MYSQL_DATABASE: {project}",
                f"      MYSQL_USER: {project}",
                "      MYSQL_PASSWORD: secret",
                "      MYSQL_ROOT_PASSWORD: secret",
                "    healthcheck:",
                '      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-psecret"]',
                "      interval: 5s",
                "      timeout: 5s",
                "      retries: 30",
                "    volumes:",
                "      - db-data:/var/lib/mysql",
            ]
        )
    else:
        lines.extend(
            [
                "    environment:",
                f"      POSTGRES_DB: {project}",
                f"      POSTGRES_USER: {project}",
                "      POSTGRES_PASSWORD: secret",
                "    healthcheck:",
                f'      test: ["CMD-SHELL", "pg_isready -U {project} -d {project}"]',
                "      interval: 5s",
                "      timeout: 5s",
                "      retries: 30",
                "    volumes:",
                "      - db-data:/var/lib/postgresql/data",
            ]
        )
    lines.extend(["", "volumes:", "  db-data:", ""])
    return "\n".join(lines)


def readme(
    ir: dict,
    target_label: str,
    commands: dict[str, list[str]],
    layout: list[str],
    scenario_path: str = "tests/api_scenario.json",
) -> str:
    auth = ir.get("auth")
    lines = [
        f"# {ir['project']}",
        "",
        f"Target: {target_label}",
        "",
        f"Generated by SEMARC version {SEMARC_VERSION} from a semantic architecture specification.",
        "After generation this project is yours: edit it like any hand-written codebase.",
        "",
        "## Quick start",
        "",
        "```bash",
        *commands["local"],
        "```",
        "",
        "## Docker",
        "",
        "```bash",
        "docker compose up --build",
        "```",
        "",
        "The container applies migrations on start and serves the API on the port shown above.",
        "",
        "## Tests",
        "",
        "```bash",
        *commands["test"],
        "```",
        "",
        f"`{scenario_path}` is the behaviour contract SEMARC derived from the specification;",
        "the test runner replays it against the application.",
        "",
        "## Configuration",
        "",
        "Settings come from environment variables or a `.env` file (see `.env.example`).",
        "`DB_CONNECTION` selects `mysql`, `pgsql` or `sqlite`.",
    ]
    if auth:
        lines.extend(
            [
                "",
                "## Authentication",
                "",
                f"`POST /register` creates a {auth['model']} and returns a JWT; `POST /login` exchanges "
                f"`{auth['identity_field']}` and `{auth['secret_field']}` for a token; `GET /me` returns the caller.",
                "Send the token as `Authorization: Bearer <token>`. Tokens are HS256 signed with `JWT_SECRET`",
                f"(at least 32 characters) and expire after `JWT_TTL` seconds (default {auth['token_ttl_seconds']}).",
            ]
        )
    lines.extend(
        [
            "",
            "## API",
            "",
            "| Method | Path | Access | Behaviour |",
            "| --- | --- | --- | --- |",
            "| GET | / | public | Project overview page |",
            "| GET | /health | public | Health and database check |",
            "| GET | /routes | public | Route discovery |",
        ]
    )
    lines.extend(
        f"| {route['method']} | {route['path']} | {route['access']} | {_behaviour(route)} |"
        for route in ir["routes"]
    )
    lines.extend(
        [
            "",
            "Successful responses wrap the payload in a `data` key. Lists also return a `meta` object with",
            "`total`, `limit` and `offset`, and accept `?limit=` (max 100) and `?offset=`. Errors return an",
            "`error` object with `code`, `message` and, for validation and conflicts, field level `details`.",
            "",
            "## Layout",
            "",
            *[f"- {entry}" for entry in layout],
            "",
        ]
    )
    return "\n".join(lines)


def _behaviour(route: dict) -> str:
    operation = route["operation"]
    model = operation.get("model")
    return {
        "list": f"List {model} records",
        "read": f"Read one {model}",
        "create": f"Create a {model}",
        "replace": f"Replace a {model}",
        "update": f"Partially update a {model}",
        "delete": f"Delete a {model}",
        "list_related": f"List {model} records of a {operation.get('parent_model')}",
        "auth_register": "Register and receive a token",
        "auth_login": "Exchange credentials for a token",
        "auth_me": "Current authenticated user",
        "custom": "Declared, not generated (returns 501 until implemented)",
    }[operation["kind"]]

"""Runtime settings shared by every target: environment, Docker Compose, README.

All targets read the same environment variables (DB_CONNECTION, DB_HOST, ...,
JWT_SECRET, JWT_TTL), so a generated project can be switched between MySQL,
PostgreSQL and SQLite without regenerating it.
"""
from semarc.compiler.version import SEMARC_VERSION
from semarc.generator.utils.inflector import snake_case
from semarc.generator.utils.resource_views import database_engine, mail_enabled, oauth_env_names, oauth_providers

MAILPIT_IMAGE = "axllent/mailpit:v1.32.0"

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
        values["JWT_REFRESH_TTL"] = str(ir["auth"]["features"]["refresh_tokens"]["ttl_seconds"])
        values["AUTH_RATE_LIMIT"] = str(ir["auth"]["rate_limit"]["attempts"])
        values["AUTH_RATE_WINDOW"] = str(ir["auth"]["rate_limit"]["window_seconds"])
        if ir["auth"].get("features", {}).get("roles"):
            values["BOOTSTRAP_ADMIN_EMAIL"] = ""
    if mail_enabled(ir):
        values.update(
            {
                "APP_URL": "http://localhost:8000",
                "MAIL_DRIVER": "log",
                "MAIL_HOST": "127.0.0.1",
                "MAIL_PORT": "1025",
                "MAIL_USERNAME": "",
                "MAIL_PASSWORD": "",
                "MAIL_ENCRYPTION": "none",
                "MAIL_FROM": f"no-reply@{snake_case(ir['project']).replace('_', '-')}.local",
            }
        )
    for provider in oauth_providers(ir):
        names = oauth_env_names(provider)
        for setting in ["client_id", "client_secret", "redirect_uri"]:
            values[names[setting]] = ""
    return values


def env_example(ir: dict) -> str:
    lines = [
        "# Copy to .env and adjust. Environment variables override this file.",
        "# DB_CONNECTION accepts mysql, pgsql or sqlite.",
        "# CORS_ORIGINS is * or a comma separated list such as https://app.example.com.",
    ]
    if ir.get("auth"):
        lines.append("# JWT_SECRET must be at least 32 characters; replace it before deploying.")
        if ir["auth"].get("features", {}).get("roles"):
            lines.append("# BOOTSTRAP_ADMIN_EMAIL: the account registering with this email becomes admin.")
    if mail_enabled(ir):
        lines.append("# MAIL_DRIVER: smtp, log (write emails to the log) or memory (tests). MAIL_ENCRYPTION: none, tls or ssl.")
    if oauth_providers(ir):
        lines.append("# OAUTH_*: credentials of the OAuth app; REDIRECT_URI is the front-end page that receives ?code=&state=.")
    lines.extend(f"{key}={value}" for key, value in env_values(ir).items())
    return "\n".join(lines) + "\n"


def docker_compose(ir: dict, port: int, web_server: dict | None = None) -> str:
    """Compose file with the app, an optional front web server and the database.

    web_server = {"image": ..., "config": ..., "mount": ...} puts a web server in front of
    the app (PHP uses nginx in front of php-fpm); the web server then owns the public port.
    """
    engine = database_engine(ir)
    lines = ["services:"]
    lines += _app_service(ir, port, engine, publish_port=web_server is None)
    if web_server:
        lines += [
            "",
            "  web:",
            f"    image: {web_server['image']}",
            "    ports:",
            f'      - "${{APP_PORT:-{port}}}:{port}"',
            "    volumes:",
            f"      - ./{web_server['config']}:{web_server['mount']}:ro",
            "    depends_on:",
            "      - app",
        ]
    if mail_enabled(ir):
        lines += [
            "",
            "  mailpit:",
            f"    image: {MAILPIT_IMAGE}",
            "    ports:",
            '      - "${MAIL_UI_PORT:-8025}:8025"',
        ]
    if engine == "SQLITE":
        lines += ["", "volumes:", "  app-storage:", ""]
        return "\n".join(lines)
    lines += _database_service(ir, engine)
    lines += ["", "volumes:", "  db-data:", ""]
    return "\n".join(lines)


def _app_service(ir: dict, port: int, engine: str, publish_port: bool) -> list[str]:
    project = snake_case(ir["project"])
    settings = DATABASES[engine]
    lines = ["  app:", "    build: ."]
    if publish_port:
        lines += ["    ports:", f'      - "${{APP_PORT:-{port}}}:{port}"']
    lines += [
        "    environment:",
        f"      APP_NAME: {ir['project']}",
        "      APP_ENV: production",
        "      CORS_ORIGINS: ${CORS_ORIGINS:-*}",
    ]
    if engine == "SQLITE":
        lines += ["      DB_CONNECTION: sqlite", "      DB_DATABASE: storage/database.sqlite"]
    else:
        lines += [
            f"      DB_CONNECTION: {settings['connection']}",
            "      DB_HOST: db",
            f'      DB_PORT: "{settings["port"]}"',
            f"      DB_DATABASE: {project}",
            f"      DB_USERNAME: {project}",
            "      DB_PASSWORD: secret",
        ]
    if ir.get("auth"):
        lines.append(f"      JWT_SECRET: ${{JWT_SECRET:-{DEV_JWT_SECRET}}}")
        if ir["auth"].get("features", {}).get("roles"):
            lines.append("      BOOTSTRAP_ADMIN_EMAIL: ${BOOTSTRAP_ADMIN_EMAIL:-}")
    if mail_enabled(ir):
        lines += [
            f"      APP_URL: ${{APP_URL:-http://localhost:{port}}}",
            "      MAIL_DRIVER: smtp",
            "      MAIL_HOST: mailpit",
            '      MAIL_PORT: "1025"',
            "      MAIL_ENCRYPTION: none",
            f"      MAIL_FROM: no-reply@{snake_case(ir['project']).replace('_', '-')}.local",
        ]
    for provider in oauth_providers(ir):
        lines += [f"      {name}: ${{{name}:-}}" for name in oauth_env_names(provider).values()]
    if engine == "SQLITE":
        lines += ["    volumes:", "      - app-storage:/app/storage"]
    else:
        lines += ["    depends_on:", "      db:", "        condition: service_healthy"]
    return lines


def _database_service(ir: dict, engine: str) -> list[str]:
    project = snake_case(ir["project"])
    lines = ["", "  db:", f"    image: {DATABASES[engine]['image']}", "    environment:"]
    if engine == "MYSQL":
        lines += [
            f"      MYSQL_DATABASE: {project}",
            f"      MYSQL_USER: {project}",
            "      MYSQL_PASSWORD: secret",
            "      MYSQL_ROOT_PASSWORD: secret",
            "    healthcheck:",
            '      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1", "-uroot", "-psecret"]',
        ]
        volume = "/var/lib/mysql"
    else:
        lines += [
            f"      POSTGRES_DB: {project}",
            f"      POSTGRES_USER: {project}",
            "      POSTGRES_PASSWORD: secret",
            "    healthcheck:",
            f'      test: ["CMD-SHELL", "pg_isready -U {project} -d {project}"]',
        ]
        volume = "/var/lib/postgresql/data"
    lines += ["      interval: 5s", "      timeout: 5s", "      retries: 30", "    volumes:", f"      - db-data:{volume}"]
    return lines


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
        f"| {route['method']} | {route['path']} | {_access_label(route)} | {_behaviour(route)} |"
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


def _access_label(route: dict) -> str:
    if route.get("roles"):
        return "role: " + ", ".join(route["roles"])
    return route["access"]


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
        "auth_set_role": "Change a user's role",
        "auth_refresh": "Exchange a refresh token for new tokens",
        "auth_logout": "Revoke a refresh token",
        "auth_change_password": "Change the current user's password",
        "auth_forgot_password": "Email a password reset token",
        "auth_reset_password": "Set a new password with a reset token",
        "auth_verify_email": "Confirm an email address with a token",
        "auth_resend_verification": "Send a new verification email",
        "auth_oauth_start": f"Start sign-in with {operation.get('provider')}",
        "auth_oauth_callback": f"Finish sign-in with {operation.get('provider')}",
        "custom": "Declared, not generated (returns 501 until implemented)",
    }[operation["kind"]]

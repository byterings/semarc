import json

from generator.php.base import PHP_HEADER, PhpFileWriter
from generator.php.php_syntax import php_literal
from generator.utils.api_scenario import ApiScenarioBuilder
from generator.utils.project_runtime import database_settings, docker_compose, env_example, readme

PORT = 8000


class ProjectGenerator:
    """Writes the runnable project shell: bootstrap, config, entry points, tests, Docker."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict, sources: list[str]) -> None:
        self._bootstrap(sources)
        self.writer.render("public/index.php", "project/index.php.tpl")
        self.writer.write(
            "public/.htaccess",
            "RewriteEngine On\nRewriteCond %{REQUEST_FILENAME} !-f\nRewriteRule ^ index.php [QSA,L]\n",
            "php htaccess",
        )
        self._config(ir)
        self.writer.render("bin/migrate.php", "project/migrate.php.tpl")
        self.writer.render("tests/run.php", "project/run.php.tpl")
        self.writer.write(
            "tests/api_scenario.json",
            json.dumps(ApiScenarioBuilder().build(ir), indent=2) + "\n",
            "api scenario",
        )
        self.writer.write("storage/.gitignore", "*\n!.gitignore\n", "storage gitignore")
        self.writer.write(".gitignore", ".env\nstorage/*.sqlite\n", "gitignore")
        self.writer.write(".env.example", env_example(ir), "env example")
        self.writer.render("Dockerfile", "project/Dockerfile.tpl")
        self.writer.write("docker-compose.yml", docker_compose(ir, PORT), "docker compose")
        self.writer.write(
            "README.md",
            readme(
                ir,
                "PHP 8.1+ (no framework, PDO)",
                {
                    "local": [
                        "cp .env.example .env",
                        "php bin/migrate.php",
                        f"php -S 127.0.0.1:{PORT} -t public public/index.php",
                    ],
                    "test": ["php tests/run.php"],
                },
                [
                    "`routes.php` registers every endpoint and its access policy",
                    "`controllers/` HTTP actions, `services/` business rules, `repositories/` SQL, `models/` field metadata",
                    "`core/` the small runtime (router, request/response, PDO, migrations)",
                    "`migrations/` table definitions applied by `php bin/migrate.php`",
                ],
            ),
            "project README",
        )

    def _bootstrap(self, sources: list[str]) -> None:
        requires = "\n".join(
            f"require_once __DIR__ . '/{source}';" for source in sources if source != "core/Env.php"
        )
        content = "\n".join(
            [
                PHP_HEADER,
                "require_once __DIR__ . '/core/Env.php';",
                "",
                "Env::load(__DIR__ . '/.env');",
                "",
                requires,
                "",
            ]
        )
        self.writer.write("bootstrap.php", content, "php bootstrap")

    def _config(self, ir: dict) -> None:
        settings = database_settings(ir)
        self.writer.write(
            "config/app.php",
            f"{PHP_HEADER}\nreturn [\n    'name' => Env::get('APP_NAME', {php_literal(ir['project'])}),\n"
            "    'env' => Env::get('APP_ENV', 'local'),\n];\n",
            "php app config",
        )
        self.writer.write(
            "config/database.php",
            "\n".join(
                [
                    PHP_HEADER,
                    f"$driver = Env::get('DB_CONNECTION', {php_literal(settings['connection'])});",
                    f"$database = Env::get('DB_DATABASE', {php_literal(settings['database'])});",
                    "if ($driver === 'sqlite' && $database !== ':memory:' && !str_starts_with($database, '/')) {",
                    "    $database = dirname(__DIR__) . '/' . $database;",
                    "}",
                    "",
                    "return [",
                    "    'driver' => $driver,",
                    "    'host' => Env::get('DB_HOST', '127.0.0.1'),",
                    f"    'port' => Env::get('DB_PORT', {php_literal(settings['port'] or '3306')}),",
                    "    'database' => $database,",
                    f"    'username' => Env::get('DB_USERNAME', {php_literal(settings['username'])}),",
                    "    'password' => Env::get('DB_PASSWORD', ''),",
                    "];",
                    "",
                ]
            ),
            "php database config",
        )

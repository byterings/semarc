from semarc.compiler.version import SEMARC_VERSION
from semarc.generator.php.base import PHP_HEADER, PhpFileWriter
from semarc.generator.php.php_syntax import php_literal
from semarc.generator.utils.inflector import pascal_case
from semarc.generator.utils.resource_views import all_route_labels


class RoutesGenerator:
    """Registers every IR route on the router with its access policy."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> None:
        project = {
            "project": ir["project"],
            "target": "PHP",
            "semarc_version": SEMARC_VERSION,
            "models": [model["name"] for model in ir["models"]],
            "routes": all_route_labels(ir),
        }
        lines = [PHP_HEADER, "$router = new Router();", ""]
        if ir.get("auth"):
            lines.extend(
                [
                    "$router->useAuthenticator(static function (Request $request): void {",
                    "    (new AuthMiddleware())->authenticate($request);",
                    "});",
                    "",
                ]
            )
        lines.extend(
            [
                f"$project = {php_literal(project, 0)};",
                "",
                "$router->add('GET', '/', static fn (): Response => Response::html(HomePage::render($project)));",
                "$router->add('GET', '/health', static function () use ($project): Response {",
                "    try {",
                "        Database::connection()->query('SELECT 1');",
                "        $database = 'ok';",
                "    } catch (Throwable $exception) {",
                "        error_log((string) $exception);",
                "        $database = 'unavailable';",
                "    }",
                "",
                "    return Response::json(",
                "        ['status' => $database === 'ok' ? 'ok' : 'degraded', 'project' => $project['project'], 'database' => $database],",
                "        $database === 'ok' ? 200 : 503,",
                "    );",
                "});",
                "$router->add('GET', '/routes', static fn (): array => ['routes' => $router->routes()]);",
                "$router->add('GET', '/openapi.json', static fn (): Response => Response::file((string) file_get_contents(__DIR__ . '/openapi.json'), 'application/json; charset=utf-8'));",
                "$router->add('GET', '/docs', static fn (): Response => Response::file((string) file_get_contents(__DIR__ . '/docs.html'), 'text/html; charset=utf-8'));",
                "",
            ]
        )
        lines.extend(self._route(route) for route in ir["routes"])
        lines.extend(["", "return $router;", ""])
        self.writer.write("routes.php", "\n".join(lines), "php routes")

    def _route(self, route: dict) -> str:
        operation = route["operation"]
        kind = operation["kind"]
        protected = ", true" if route["access"] == "protected" else ""
        if route.get("roles"):
            protected = f", true, {php_literal(route['roles'])}"
        prefix = f"$router->add('{route['method']}', '{route['path']}', "

        if kind == "auth_set_role":
            return f"{prefix}static fn (Request $request, array $params): array => (new RoleController())->update($request, $params['id']){protected});"
        if kind in {"auth_oauth_start", "auth_oauth_callback"}:
            action = "oauthStart" if kind == "auth_oauth_start" else "oauthCallback"
            return f"{prefix}static fn (Request $request): array => (new AuthController())->{action}($request, {php_literal(operation['provider'])}){protected});"
        if kind.startswith("auth_"):
            action = pascal_case(kind.removeprefix("auth_"))
            action = action[:1].lower() + action[1:]
            return_type = "array" if action in {"login", "me", "refresh", "verifyEmail"} else "Response"
            return f"{prefix}static fn (Request $request): {return_type} => (new AuthController())->{action}($request){protected});"

        if kind == "custom":
            message = (
                f"{route['method']} {route['path']} is declared in the semantic source but has no generated behaviour. "
                "Implement it in routes.php."
            )
            return f"{prefix}static fn (): never => throw HttpException::notImplemented({php_literal(message)}){protected});"

        controller = f"(new {operation['model']}Controller())"
        if kind == "list":
            return f"{prefix}static fn (Request $request): array => {controller}->list($request){protected});"
        if kind == "create":
            return f"{prefix}static fn (Request $request): Response => {controller}->create($request){protected});"
        parameter = operation["parameter"]
        if kind == "list_related":
            action = f"listBy{pascal_case(operation['parent_model'])}"
            return f"{prefix}static fn (Request $request, array $params): array => {controller}->{action}($request, $params['{parameter}']){protected});"
        return_type = "Response" if kind == "delete" else "array"
        return f"{prefix}static fn (Request $request, array $params): {return_type} => {controller}->{kind}($request, $params['{parameter}']){protected});"

from compiler.version import SEMARC_VERSION
from generator.php.base import PHP_HEADER, PhpFileWriter
from generator.php.php_syntax import php_literal
from generator.utils.inflector import pascal_case
from generator.utils.resource_views import all_route_labels


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
        prefix = f"$router->add('{route['method']}', '{route['path']}', "

        if kind.startswith("auth_"):
            action = kind.removeprefix("auth_")
            return_type = "Response" if action == "register" else "array"
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

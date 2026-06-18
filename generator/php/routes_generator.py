from pathlib import Path

from generator.php.template_engine import TemplateEngine
from generator.utils.inflector import resource_path
from generator.utils.project_experience import SEMARC_VERSION, complete_routes, model_names, module_names, profile_names, route_lines


class RoutesGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        route_blocks = [
            self._home_route_block(ir),
            self._health_route_block(ir),
            self._route_discovery_block(ir),
        ]
        route_blocks.extend(self._route_block(route, ir) for route in complete_routes(ir))
        template = "routes.tpl"
        content = self.template_engine.render(
            template,
            {
                "requires": self._requires(ir),
                "route_blocks": "\n".join(route_blocks),
            },
        )
        path = self.output_dir / "routes.php"
        path.write_text(content, encoding="utf-8")
        self._report(path, template)

    def _requires(self, ir: dict) -> str:
        controllers = set()
        if any(route["path"] == "/login" for route in complete_routes(ir)):
            controllers.add("AuthController")
        for route in complete_routes(ir):
            model_name = self._model_for_route(route, ir["models"])
            if model_name:
                controllers.add(f"{model_name}Controller")
        return "\n".join(
            f"require_once __DIR__ . '/controllers/{controller}.php';"
            for controller in sorted(controllers)
        )

    def _route_block(self, route: dict, ir: dict) -> str:
        handler = route.get("handler", {})
        lines = [f"if ($method === '{route['method']}' && $path === '{route['path']}') {{"]

        if handler.get("type") == "controller":
            controller = handler["component"]
            action = handler["action"]
            lines.extend(
                [
                    f"    $controller = new {controller}();",
                    f"    $controller->{action}();",
                ]
            )
        else:
            model_name = self._model_for_route(route, ir["models"])
            if model_name:
                action = "store" if route["method"] == "POST" else "index"
                lines.extend(
                    [
                        f"    $controller = new {model_name}Controller();",
                        f"    $controller->{action}();",
                    ]
                )
            else:
                lines.extend(
                    [
                        "    http_response_code(501);",
                        "    header('Content-Type: application/json');",
                        "    echo json_encode(['error' => 'Generated TODO: connect this route to a business service.']);",
                    ]
                )

        lines.extend(["    exit;", "}", ""])
        return "\n".join(lines)

    def _model_for_route(self, route: dict, models: list[dict]) -> str | None:
        first_segment = route["path"].strip("/").split("/", 1)[0].lower()
        if not first_segment:
            return None
        for model in models:
            segment = self._segment_name(model["name"])
            if first_segment in {segment, self._pluralize(segment)}:
                return model["name"]
        return None

    def _home_route_block(self, ir: dict) -> str:
        html = self._php_array(
            {
                "project": ir["project"],
                "target": "PHP",
                "semarc_version": SEMARC_VERSION,
                "models": model_names(ir),
                "routes": ["GET /", "GET /health", "GET /routes"] + route_lines(ir),
                "profiles": profile_names(ir),
                "modules": module_names(ir),
                "status": "Running",
            }
        )
        return "\n".join(
            [
                "if ($method === 'GET' && $path === '/') {",
                "    header('Content-Type: text/html; charset=utf-8');",
                f"    $project = {html};",
                "    echo '<h1>SEMARC Generated Project</h1>';",
                "    echo '<p><strong>Project:</strong> ' . htmlspecialchars($project['project']) . '</p>';",
                "    echo '<p><strong>Target:</strong> ' . htmlspecialchars($project['target']) . '</p>';",
                "    echo '<p><strong>SEMARC Version:</strong> ' . htmlspecialchars($project['semarc_version']) . '</p>';",
                "    echo '<h2>Models</h2><ul>';",
                "    foreach ($project['models'] as $item) { echo '<li>' . htmlspecialchars($item) . '</li>'; }",
                "    echo '</ul><h2>Routes</h2><ul>';",
                "    foreach ($project['routes'] as $item) { echo '<li>' . htmlspecialchars($item) . '</li>'; }",
                "    echo '</ul><p><strong>Status:</strong> ' . htmlspecialchars($project['status']) . '</p>';",
                "    exit;",
                "}",
                "",
            ]
        )

    def _health_route_block(self, ir: dict) -> str:
        return "\n".join(
            [
                "if ($method === 'GET' && $path === '/health') {",
                "    header('Content-Type: application/json');",
                f"    echo json_encode(['status' => 'ok', 'project' => '{ir['project']}']);",
                "    exit;",
                "}",
                "",
            ]
        )

    def _route_discovery_block(self, ir: dict) -> str:
        routes = self._php_array(["GET /", "GET /health", "GET /routes"] + route_lines(ir))
        return "\n".join(
            [
                "if ($method === 'GET' && $path === '/routes') {",
                "    header('Content-Type: application/json');",
                f"    echo json_encode(['routes' => {routes}]);",
                "    exit;",
                "}",
                "",
            ]
        )

    def _segment_name(self, value: str) -> str:
        output = []
        for index, char in enumerate(value):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output).replace("_", "-")

    def _pluralize(self, value: str) -> str:
        return resource_path(value)

    def _php_array(self, value) -> str:
        if isinstance(value, dict):
            entries = ", ".join(f"'{key}' => {self._php_array(item)}" for key, item in value.items())
            return "[" + entries + "]"
        if isinstance(value, list):
            entries = ", ".join(self._php_array(item) for item in value)
            return "[" + entries + "]"
        return "'" + str(value).replace("'", "\\'") + "'"

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

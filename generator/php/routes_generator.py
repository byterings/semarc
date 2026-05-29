from pathlib import Path

from generator.php.template_engine import TemplateEngine


class RoutesGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        route_blocks = [self._route_block(route) for route in ir["routes"]]
        template = "routes.tpl"
        content = self.template_engine.render(
            template,
            {
                "requires": "require_once __DIR__ . '/controllers/AuthController.php';",
                "route_blocks": "\n".join(route_blocks),
            },
        )
        path = self.output_dir / "routes.php"
        path.write_text(content, encoding="utf-8")
        self._report(path, template)

    def _route_block(self, route: dict) -> str:
        handler = route["handler"]
        lines = [f"if ($method === '{route['method']}' && $path === '{route['path']}') {{"]

        if handler["type"] == "controller":
            controller = handler["component"]
            action = handler["action"]
            lines.extend(
                [
                    f"    $controller = new {controller}();",
                    f"    $controller->{action}();",
                ]
            )
        elif handler["payload"] == "data":
            lines.extend(
                [
                    "    header('Content-Type: application/json');",
                    "    echo json_encode(['data' => []]);",
                ]
            )
        else:
            lines.extend(
                [
                    "    header('Content-Type: application/json');",
                    "    echo json_encode(['message' => 'Endpoint generated']);",
                ]
            )

        lines.extend(["    exit;", "}", ""])
        return "\n".join(lines)

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

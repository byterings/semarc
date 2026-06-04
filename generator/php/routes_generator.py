from pathlib import Path

from generator.php.template_engine import TemplateEngine


class RoutesGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        route_blocks = [self._route_block(route, ir) for route in ir["routes"]]
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
        if any(route["path"] == "/login" for route in ir["routes"]):
            controllers.add("AuthController")
        for route in ir["routes"]:
            model_name = self._model_for_route(route, ir["models"])
            if model_name:
                controllers.add(f"{model_name}Controller")
        return "\n".join(
            f"require_once __DIR__ . '/controllers/{controller}.php';"
            for controller in sorted(controllers)
        )

    def _route_block(self, route: dict, ir: dict) -> str:
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

    def _segment_name(self, value: str) -> str:
        output = []
        for index, char in enumerate(value):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output).replace("_", "-")

    def _pluralize(self, value: str) -> str:
        if value.endswith("y"):
            return value[:-1] + "ies"
        if value.endswith("s"):
            return value
        return value + "s"

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

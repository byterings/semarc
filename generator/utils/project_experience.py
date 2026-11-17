from compiler.version import SEMARC_VERSION
from generator.utils.inflector import resource_path


def complete_routes(ir: dict) -> list[dict]:
    routes = [
        {
            "method": route["method"],
            "path": route["path"],
            "handler": dict(route.get("handler", {})),
            "model": model_for_route(route["path"], ir.get("models", [])),
        }
        for route in ir.get("routes", [])
    ]
    existing = {(route["method"], route["path"]) for route in routes}
    for model in ir.get("models", []):
        path = "/" + resource_path(model["name"])
        if ("GET", path) not in existing:
            routes.append({"method": "GET", "path": path, "model": model["name"]})
    return routes


def model_for_route(path: str, models: list[dict]) -> str | None:
    first_segment = path.strip("/").split("/", 1)[0].replace("-", "_").lower()
    if not first_segment:
        return None
    for model in models:
        singular = model["name"].replace("-", "_").lower()
        snake = _snake_case(model["name"])
        if first_segment in {singular, snake, resource_path(model["name"]).replace("-", "_")}:
            return model["name"]
    return None


def route_lines(ir: dict) -> list[str]:
    return [f"{route['method']} {route['path']}" for route in complete_routes(ir)]


def model_names(ir: dict) -> list[str]:
    return [model["name"] for model in ir.get("models", [])]


def profile_names(ir: dict) -> list[str]:
    return []


def module_names(ir: dict) -> list[str]:
    return []


def _snake_case(value: str) -> str:
    output = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            output.append("_")
        output.append(char.lower())
    return "".join(output)

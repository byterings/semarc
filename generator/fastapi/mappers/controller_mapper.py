from generator.fastapi.mappers.name_utils import snake_case


class ControllerMapper:
    """Maps IR routes/controllers into FastAPI router modules."""

    def map(self, ir: dict) -> list[dict]:
        mapped = []
        if any(route["path"] == "/login" for route in ir["routes"]):
            mapped.append(
                {
                    "path": "routers/auth.py",
                    "template": "routers/auth_router.tpl",
                    "values": {
                        "project_name": ir["project"],
                    },
                }
            )

        for model in ir["models"]:
            routes = self._routes_for_model(model["name"], ir["routes"])
            if not routes:
                continue
            snake = snake_case(model["name"])
            mapped.append(
                {
                    "path": f"routers/{snake}.py",
                    "template": "routers/model_router.tpl",
                    "values": {
                        "model_name": model["name"],
                        "router_prefix": "/" + self._pluralize(snake),
                        "service_name": f"{model['name']}Service",
                        "service_module": f"{snake}_service",
                        "service_variable": f"{snake}_service",
                        "methods": self._methods(model["name"], routes),
                    },
                }
            )

        return mapped

    def _routes_for_model(self, model_name: str, routes: list[dict]) -> list[dict]:
        snake = snake_case(model_name)
        return [
            route
            for route in routes
            if self._first_segment(route["path"]) in {snake, self._pluralize(snake)}
        ]

    def _methods(self, model_name: str, routes: list[dict]) -> str:
        blocks = []
        service_variable = f"{snake_case(model_name)}_service"
        for route in routes:
            if route["method"] == "GET":
                blocks.append(
                    "\n".join(
                        [
                            "@router.get(\"\")",
                            "def list_records():",
                            f"    return {{\"data\": {service_variable}.list()}}",
                        ]
                    )
                )
            elif route["method"] == "POST":
                blocks.append(
                    "\n".join(
                        [
                            "@router.post(\"\")",
                            "def create_record(payload: dict):",
                            f"    return {service_variable}.create(payload)",
                        ]
                    )
                )
            else:
                blocks.append(
                    "\n".join(
                        [
                            f"@router.api_route(\"\", methods=[\"{route['method']}\"])",
                            "def generated_todo():",
                            "    return {\"status\": \"TODO: connect this route to a business service\"}",
                        ]
                    )
                )
        return "\n\n".join(blocks)

    def _first_segment(self, path: str) -> str:
        parts = [part for part in path.strip("/").split("/") if part]
        return parts[0].replace("-", "_").lower() if parts else ""

    def _pluralize(self, value: str) -> str:
        if value.endswith("y"):
            return value[:-1] + "ies"
        if value.endswith("s"):
            return value
        return value + "s"

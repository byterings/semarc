from generator.fastapi.mappers.name_utils import snake_case


class MiddlewareMapper:
    """Maps IR middleware into FastAPI middleware modules."""

    def map(self, ir: dict) -> list[dict]:
        mapped = [
            {
                "path": "middleware/token_validation_middleware.py",
                "template": "middleware/token_validation_middleware.tpl",
                "values": {},
            }
        ]

        for middleware in ir["middlewares"]:
            mapped.append(
                {
                    "path": f"middleware/{snake_case(middleware['name'])}.py",
                    "template": "middleware/auth_middleware.tpl",
                    "values": {},
                }
            )

        return mapped

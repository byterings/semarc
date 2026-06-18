class MiddlewareMapper:
    """Maps IR middleware into FastAPI middleware modules."""

    def map(self, ir: dict) -> list[dict]:
        return [
            {
                "path": "middleware/token_validation_middleware.py",
                "template": "middleware/token_validation_middleware.tpl",
                "values": {},
            }
        ]

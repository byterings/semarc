class ControllerMapper:
    """Maps IR routes/controllers into FastAPI router modules."""

    def map(self, ir: dict) -> list[dict]:
        return [
            {
                "path": "routers/auth.py",
                "template": "routers/auth_router.tpl",
                "values": {
                    "project_name": ir["project"],
                },
            }
        ]

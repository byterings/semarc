class ConfigMapper:
    """Maps IR config into FastAPI settings."""

    def map(self, ir: dict) -> list[dict]:
        database = ir["config"]["database"]
        return [
            {
                "path": "config/settings.py",
                "template": "config/settings.tpl",
                "values": {
                    "app_name": ir["project"],
                    "secret_key": f"{ir['project']}_prototype_secret",
                    "database_engine": database["engine"],
                },
            }
        ]

class StrategyEngine:
    """Selects implementation strategy without changing semantic meaning."""

    TARGET_PROFILES = {
        "PHP": {
            "target": "PHP",
            "generator": "php",
            "framework": "none",
            "auth_strategy": "lightweight_custom_token",
            "repository_strategy": "in_memory_prototype",
        },
        "LARAVEL": {
            "target": "PHP",
            "generator": "php",
            "framework": "laravel-profile-placeholder",
            "auth_strategy": "lightweight_custom_token",
            "repository_strategy": "in_memory_prototype",
        },
        "FASTAPI": {
            "target": "FASTAPI",
            "generator": "fastapi",
            "framework": "fastapi",
            "auth_strategy": "lightweight_custom_token",
            "repository_strategy": "in_memory_prototype",
        },
        "NESTJS": {
            "target": "NESTJS",
            "generator": "nestjs",
            "framework": "nestjs",
            "auth_strategy": "placeholder_guard",
            "repository_strategy": "service_skeleton",
        },
        "NODE": {
            "target": "NODE",
            "generator": "node",
            "framework": "node-profile-placeholder",
            "auth_strategy": "lightweight_custom_token",
            "repository_strategy": "in_memory_prototype",
        },
    }

    def select(self, architecture, target_override: str | None = None) -> dict:
        target = target_override.upper() if target_override else architecture.target.name if architecture.target else "PHP"
        return self.TARGET_PROFILES.get(target, self.TARGET_PROFILES["PHP"])

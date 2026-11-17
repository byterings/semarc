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
    }

    def select(self, architecture, target_override: str | None = None) -> dict:
        target = target_override.upper() if target_override else architecture.target.name if architecture.target else "PHP"
        if target not in self.TARGET_PROFILES:
            raise ValueError(f"No target profile registered for: {target}")
        return dict(self.TARGET_PROFILES[target])

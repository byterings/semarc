from generator.targets.target import TargetDefinition


class TargetRegistry:
    """Registry for built-in and future target package metadata."""

    def __init__(self) -> None:
        self._targets: dict[str, TargetDefinition] = {}

    def register(self, target: TargetDefinition) -> None:
        self._targets[target.name.lower()] = target

    def get(self, name: str) -> TargetDefinition | None:
        return self._targets.get(name.lower())

    def all(self) -> list[TargetDefinition]:
        return [self._targets[name] for name in sorted(self._targets)]

    @classmethod
    def builtins(cls) -> "TargetRegistry":
        registry = cls()
        registry.register(
            TargetDefinition(
                name="php",
                language="PHP",
                description="Runnable core PHP project generator",
                generator="php",
            )
        )
        registry.register(
            TargetDefinition(
                name="fastapi",
                language="Python",
                description="Runnable FastAPI project generator",
                generator="fastapi",
            )
        )
        registry.register(
            TargetDefinition(
                name="nestjs",
                language="TypeScript",
                description="Runnable NestJS project generator",
                generator="nestjs",
            )
        )
        return registry

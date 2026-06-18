from pathlib import Path

from generator.targets.loader import TargetLoader
from generator.targets.target import TargetCapability, TargetDefinition, TargetMetadata


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
        root = Path(__file__).resolve().parents[1]
        for path in sorted(root.glob("*/project_template/target.yaml")):
            registry.register(cls._definition_from_metadata(TargetLoader().load(path)))
        return registry

    @staticmethod
    def _definition_from_metadata(metadata: TargetMetadata) -> TargetDefinition:
        supports = set(metadata.supports)
        return TargetDefinition(
            name=metadata.name,
            language=metadata.language,
            description=metadata.description,
            generator=metadata.generator or metadata.name,
            metadata={"source_path": str(metadata.source_path or "")},
            capabilities=TargetCapability(
                supports_project_layer="project" in supports,
                supports_configuration_layer="configuration" in supports,
                supports_entity_layer="entity" in supports,
                supports_persistence_layer="persistence" in supports,
                supports_business_layer="business" in supports,
                supports_api_layer="api" in supports,
                supports_auth_layer="auth" in supports,
            ),
        )

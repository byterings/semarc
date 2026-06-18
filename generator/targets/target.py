from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TargetCapability:
    supports_project_layer: bool = True
    supports_configuration_layer: bool = True
    supports_entity_layer: bool = True
    supports_persistence_layer: bool = True
    supports_business_layer: bool = True
    supports_api_layer: bool = True
    supports_auth_layer: bool = True

    def supports(self, layer: str) -> bool:
        return {
            "project": self.supports_project_layer,
            "configuration": self.supports_configuration_layer,
            "entity": self.supports_entity_layer,
            "persistence": self.supports_persistence_layer,
            "business": self.supports_business_layer,
            "api": self.supports_api_layer,
            "auth": self.supports_auth_layer,
        }.get(layer, False)


@dataclass(frozen=True)
class TargetMetadata:
    name: str
    language: str
    description: str
    generator: str = ""
    supports: tuple[str, ...] = ()
    source_path: Path | None = None


@dataclass(frozen=True)
class TargetDefinition:
    name: str
    language: str
    description: str
    generator: str
    metadata: dict[str, str] = field(default_factory=dict)
    capabilities: TargetCapability = field(default_factory=TargetCapability)

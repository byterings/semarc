from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TargetMetadata:
    name: str
    language: str
    description: str
    source_path: Path | None = None


@dataclass(frozen=True)
class TargetDefinition:
    name: str
    language: str
    description: str
    generator: str
    metadata: dict[str, str] = field(default_factory=dict)

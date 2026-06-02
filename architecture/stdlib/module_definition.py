from dataclasses import dataclass
from dataclasses import field
from pathlib import Path


@dataclass(frozen=True)
class ModuleDefinition:
    """Metadata-only stdlib module definition."""

    name: str
    version: str
    description: str
    source_path: Path
    dependencies: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

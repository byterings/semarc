from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModuleDefinition:
    """Metadata-only stdlib module definition."""

    name: str
    version: str
    description: str
    source_path: Path

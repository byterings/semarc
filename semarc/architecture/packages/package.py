from dataclasses import dataclass, field


@dataclass(frozen=True)
class Package:
    """Metadata-only semantic package foundation object."""

    name: str
    domain: str
    description: str = ""
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

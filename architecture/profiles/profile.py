from dataclasses import dataclass, field


@dataclass(frozen=True)
class Profile:
    """Metadata-only semantic profile foundation object."""

    name: str
    description: str = ""
    extends: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

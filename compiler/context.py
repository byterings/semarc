from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CompilerContext:
    source_path: Path
    output_dir: str = "output"
    debug: bool = False
    target_override: str | None = None
    source: str = ""
    tokens: list = field(default_factory=list)
    ast: Any = None
    relationship_graph: dict = field(default_factory=dict)
    relationship_plan: dict = field(default_factory=dict)
    migration_plan: dict = field(default_factory=dict)
    constraint_result: Any = None
    architecture_report: dict = field(default_factory=dict)
    loaded_profiles: list[Any] = field(default_factory=list)
    loaded_packages: list[Any] = field(default_factory=list)
    target_profile: dict = field(default_factory=dict)
    architecture_plan: dict = field(default_factory=dict)
    dependency_graph: Any = None
    expanded_architecture: dict = field(default_factory=dict)
    ir: dict = field(default_factory=dict)
    generated_components: list[dict[str, str]] = field(default_factory=list)
    compiler_passes: list[str] = field(default_factory=list)

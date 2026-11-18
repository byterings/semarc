from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CompilerContext:
    source_path: Path
    output_dir: str = "output"
    force_output: bool = False
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
    resolved_profile_modules: list[str] = field(default_factory=list)
    loaded_packages: list[Any] = field(default_factory=list)
    loaded_modules: list[Any] = field(default_factory=list)
    resolved_modules: list[Any] = field(default_factory=list)
    dependency_resolved_modules: list[Any] = field(default_factory=list)
    module_requirements: list[str] = field(default_factory=list)
    module_conflicts: list[str] = field(default_factory=list)
    module_registry: Any = None
    architecture_analysis_report: dict = field(default_factory=dict)
    target_profile: dict = field(default_factory=dict)
    architecture_plan: dict = field(default_factory=dict)
    resource_plan: dict = field(default_factory=dict)
    dependency_graph: Any = None
    expanded_architecture: dict = field(default_factory=dict)
    ir: dict = field(default_factory=dict)
    generation_contract: Any = None
    target_contract_mapping: dict = field(default_factory=dict)
    generated_components: list[dict[str, str]] = field(default_factory=list)
    compiler_passes: list[str] = field(default_factory=list)

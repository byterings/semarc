import json
from pathlib import Path

from architecture.constraints.constraint_engine import ConstraintEngine


class DiagnosticReportPass:
    def run(self, context) -> None:
        context.compiler_passes.append("DiagnosticReportPass")
        context.constraint_result = ConstraintEngine().analyze(
            ast=context.ast,
            relationship_plan=context.relationship_plan,
            dependency_graph=context.dependency_graph,
            ir=context.ir,
        )
        context.architecture_report = context.constraint_result.to_dict()
        context.architecture_report["modules"] = [
            {
                "name": module.name,
                "version": module.version,
                "description": module.description,
                "source_path": str(module.source_path),
                "dependencies": list(module.dependencies),
                "requirements": list(module.requirements),
                "conflicts": list(module.conflicts),
            }
            for module in context.resolved_modules
        ]
        context.architecture_report["resolved_through_dependencies"] = [
            module.name for module in context.dependency_resolved_modules
        ]
        if context.loaded_profiles:
            context.architecture_report["profiles"] = [profile.name for profile in context.loaded_profiles]
        if context.resolved_profile_modules:
            context.architecture_report["modules_from_profiles"] = list(context.resolved_profile_modules)
        if context.module_requirements:
            context.architecture_report["requirements"] = list(context.module_requirements)
        if context.module_conflicts:
            context.architecture_report["conflicts"] = list(context.module_conflicts)
        if context.architecture_analysis_report:
            context.architecture_report["architecture_analysis"] = context.architecture_analysis_report

        output_dir = Path(context.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "architecture_report.json").write_text(
            json.dumps(context.architecture_report, indent=2),
            encoding="utf-8",
        )

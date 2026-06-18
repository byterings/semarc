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
        self._add_v2_report_fields(context)

        output_dir = Path(context.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "architecture_report.json").write_text(
            json.dumps(context.architecture_report, indent=2),
            encoding="utf-8",
        )

    def _add_v2_report_fields(self, context) -> None:
        analysis = context.architecture_analysis_report or {
            "warnings": [],
            "recommendations": [],
            "rules_executed": 0,
        }
        constraint_warnings = context.architecture_report.get("warnings", [])
        constraint_recommendations = context.architecture_report.get("recommendations", [])
        analysis_warnings = analysis.get("warnings", [])
        analysis_recommendations = analysis.get("recommendations", [])

        context.architecture_report["project"] = context.ast.project.name if context.ast and context.ast.project else ""
        context.architecture_report["target"] = context.target_profile.get(
            "target",
            context.ir.get("target", "PHP"),
        )
        context.architecture_report["statistics"] = {
            "models": len(context.ast.models),
            "routes": len(context.ast.routes),
            "relations": len(context.ast.relations),
            "profiles": len(context.loaded_profiles),
            "modules": len(context.resolved_modules),
            "resolved_dependencies": len(context.dependency_resolved_modules),
            "warnings": len(constraint_warnings) + len(analysis_warnings),
            "recommendations": len(constraint_recommendations) + len(analysis_recommendations),
        }
        context.architecture_report["dependencies"] = [
            {
                "module": module.name,
                "dependencies": list(module.dependencies),
            }
            for module in context.resolved_modules
            if module.dependencies
        ]
        context.architecture_report["constraints"] = {
            "score": context.architecture_report.get("score", 0),
            "rules_executed": context.architecture_report.get("rules_executed", 0),
            "errors": context.architecture_report.get("errors", []),
            "warnings": constraint_warnings,
            "recommendations": constraint_recommendations,
            "requirements": list(context.module_requirements),
            "conflicts": list(context.module_conflicts),
        }
        context.architecture_report["analysis"] = analysis
        context.architecture_report["generator"] = {
            "target": context.target_profile.get("target", context.ir.get("target", "PHP")),
            "framework": context.target_profile.get("framework", "none"),
            "generator": context.target_profile.get("generator", ""),
        }
        if context.generation_contract is not None:
            context.architecture_report["generation_contract"] = context.generation_contract.to_dict()
            context.architecture_report["target_contract_mapping"] = dict(context.target_contract_mapping)
        context.architecture_report["compilation"] = {
            "passes": list(context.compiler_passes),
            "generated_components": len(context.generated_components),
        }

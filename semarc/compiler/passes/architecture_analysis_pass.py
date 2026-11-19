from semarc.architecture.analysis import ArchitectureAnalyzer


class ArchitectureAnalysisPass:
    """Runs deterministic architecture quality analysis without mutating the compiler state."""

    def run(self, context) -> None:
        context.compiler_passes.append("ArchitectureAnalysisPass")
        result = ArchitectureAnalyzer().analyze(
            ast=context.ast,
            loaded_profiles=context.loaded_profiles,
            resolved_modules=context.resolved_modules,
            relationship_plan=context.relationship_plan,
        )
        context.architecture_analysis_report = result.to_dict()

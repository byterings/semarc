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

        output_dir = Path(context.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "architecture_report.json").write_text(
            json.dumps(context.architecture_report, indent=2),
            encoding="utf-8",
        )

from architecture.constraints.constraint_engine import ConstraintEngine


class ConstraintPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ConstraintPass")
        context.constraint_result = ConstraintEngine().analyze(
            ast=context.ast,
            relationship_plan=context.relationship_plan,
        )
        context.architecture_report = context.constraint_result.to_dict()

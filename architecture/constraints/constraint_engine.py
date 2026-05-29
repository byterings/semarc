from architecture.constraints.constraint_registry import ConstraintRegistry
from architecture.constraints.constraint_result import ConstraintResult


class ConstraintEngine:
    """Evaluates deterministic architecture constraints."""

    def __init__(self, registry: ConstraintRegistry | None = None) -> None:
        self.registry = registry or ConstraintRegistry()
        if not self.registry.rules:
            self.registry.load_defaults()

    def analyze(self, ast=None, relationship_plan=None, dependency_graph=None, ir=None) -> ConstraintResult:
        result = ConstraintResult()
        context = {
            "ast": ast,
            "relationship_plan": relationship_plan or {},
            "dependency_graph": dependency_graph,
            "ir": ir or {},
        }

        for rule in self.registry.rules:
            result.rules_executed += 1
            rule.evaluate(context, result)

        result.finalize_score()
        return result

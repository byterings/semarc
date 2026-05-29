from architecture.expander import ArchitectureExpander
from architecture.rules_engine import ArchitectureRuleEngine
from architecture.strategy_engine import StrategyEngine


class ExpansionPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ExpansionPass")
        context.target_profile = StrategyEngine().select(context.ast, context.target_override)
        context.architecture_plan, context.dependency_graph = ArchitectureRuleEngine().apply(context.ast)
        if context.target_override:
            context.architecture_plan["target"] = context.target_profile["target"]
        context.expanded_architecture = ArchitectureExpander().expand(
            context.ast,
            context.architecture_plan,
            context.target_profile,
        )
        context.expanded_architecture["relationship_plan"] = context.relationship_plan
        context.expanded_architecture["migration_plan"] = context.migration_plan

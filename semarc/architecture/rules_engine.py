from semarc.architecture.dependency_graph import DependencyGraph
from semarc.architecture.rules.auth_rules import apply_auth_rules
from semarc.architecture.rules.model_rules import apply_model_rules
from semarc.architecture.rules.route_rules import apply_route_rules


class ArchitectureRuleEngine:
    """Central rule engine that turns semantic AST intent into architecture plan."""

    def apply(self, architecture, resource_plan: dict | None = None) -> tuple[dict, DependencyGraph]:
        graph = DependencyGraph()
        plan = {
            "project": architecture.project.name,
            "target": architecture.target.name if architecture.target else "PHP",
            "database": self._database(architecture),
            "auth": None,
            "models": architecture.models,
            "routes": architecture.routes,
            "relationships": [],
            "validations": architecture.validations,
            "profiles": architecture.profiles,
            "packages": architecture.packages,
            "repositories": [],
            "validators": [],
        }

        graph.add_node("DatabaseConfig")
        apply_auth_rules(architecture, plan, graph)
        apply_model_rules(architecture, plan, graph, resource_plan)
        apply_route_rules(architecture, plan, graph, resource_plan)

        for validation in architecture.validations:
            graph.add_node(f"Validation:{validation.field_name}")
            graph.add_dependency(f"Validation:{validation.field_name}", "Validator")

        graph.validate()
        return plan, graph

    def _database(self, architecture) -> dict:
        if architecture.database is None:
            return {"engine": "NONE"}
        return {"engine": architecture.database.engine}

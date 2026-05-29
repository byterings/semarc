from compiler.diagnostics.diagnostic import DiagnosticRecommendation, DiagnosticWarning


class RelationshipDepthRule:
    code = "REL001"

    def evaluate(self, context: dict, result) -> None:
        relationship_plan = context["relationship_plan"]
        graph = relationship_plan.get("graph", {})
        if not graph:
            return

        max_depth = max((self._depth(node, graph, set()) for node in graph), default=0)
        if max_depth > 3:
            result.add_warning(
                DiagnosticWarning(
                    self.code,
                    "Relationship graph depth exceeds 3; review repository and migration complexity.",
                    "RELATION",
                )
            )
        elif graph:
            result.add_recommendation(
                DiagnosticRecommendation(
                    "REL002",
                    "Relationship graph detected; ensure generated repository methods are reviewed before production use.",
                    "RELATION",
                )
            )

    def _depth(self, node: str, graph: dict, seen: set[str]) -> int:
        if node in seen:
            return 0
        seen.add(node)
        children = graph.get(node, [])
        if not children:
            return 1
        return 1 + max(self._depth(child["model"], graph, set(seen)) for child in children)

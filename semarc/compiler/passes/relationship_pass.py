from semarc.architecture.relationship_engine import RelationshipEngine


class RelationshipPass:
    def run(self, context) -> None:
        context.compiler_passes.append("RelationshipPass")
        context.relationship_plan = RelationshipEngine().build(context.ast)
        context.relationship_graph = context.relationship_plan["graph"]
        context.migration_plan = context.relationship_plan["migrations"]

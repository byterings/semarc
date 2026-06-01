from architecture.ir_builder import ArchitectureIRBuilder


class IRPass:
    def run(self, context) -> None:
        context.compiler_passes.append("IRPass")
        context.ir = ArchitectureIRBuilder().build(context.expanded_architecture)
        context.ir["dependency_graph"] = context.dependency_graph.to_debug()
        context.ir["relationship_graph"] = context.relationship_graph
        context.ir["migrations"] = context.migration_plan
        context.ir["modules"] = [
            {
                "name": module.name,
                "version": module.version,
                "description": module.description,
            }
            for module in context.resolved_modules
        ]

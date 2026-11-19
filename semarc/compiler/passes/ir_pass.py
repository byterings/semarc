from semarc.architecture.ir_builder import ArchitectureIRBuilder


class IRPass:
    def run(self, context) -> None:
        context.compiler_passes.append("IRPass")
        context.ir = ArchitectureIRBuilder().build(context.expanded_architecture)
        context.ir["dependency_graph"] = context.dependency_graph.to_debug()
        context.ir["relationship_graph"] = context.relationship_graph
        context.ir["modules"] = [
            {
                "name": module.name,
                "version": module.version,
                "description": module.description,
                "dependencies": list(module.dependencies),
                "requirements": list(module.requirements),
                "conflicts": list(module.conflicts),
            }
            for module in context.resolved_modules
        ]
        context.ir["resolved_through_dependencies"] = [
            module.name for module in context.dependency_resolved_modules
        ]
        context.ir["profiles_loaded"] = [profile.name for profile in context.loaded_profiles]
        context.ir["modules_from_profiles"] = list(context.resolved_profile_modules)
        context.ir["module_requirements"] = list(context.module_requirements)
        context.ir["module_conflicts"] = list(context.module_conflicts)

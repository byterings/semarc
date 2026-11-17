from architecture.stdlib import ModuleDependencyError, ModuleDependencyResolver
from validator.validator import SemanticValidator
from validator.validator import SemanticValidationError


class ValidationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ValidationPass")
        validator = SemanticValidator(module_registry=context.module_registry)
        validator.validate_target_override(context.target_override)
        validator.validate(context.ast)
        direct_modules = []
        seen_modules = set()
        if context.module_registry is None:
            return

        requested_module_names = list(context.resolved_profile_modules) + [
            package.name for package in context.ast.packages
        ]
        for module_name in requested_module_names:
            module = context.module_registry.get(module_name)
            if module is None:
                continue
            module_key = module.name.lower()
            if module_key in seen_modules:
                continue
            seen_modules.add(module_key)
            direct_modules.append(module)

        try:
            resolved_modules = ModuleDependencyResolver(context.module_registry).resolve(direct_modules)
        except ModuleDependencyError as error:
            raise SemanticValidationError(f"[Semantic Error]\n{error}") from error

        direct_keys = {module.name.lower() for module in direct_modules}
        context.resolved_modules = resolved_modules
        context.dependency_resolved_modules = [
            module
            for module in resolved_modules
            if module.name.lower() not in direct_keys
        ]
        context.module_requirements = sorted(
            {
                requirement
                for module in resolved_modules
                for requirement in module.requirements
            }
        )
        context.module_conflicts = sorted(
            {
                conflict
                for module in resolved_modules
                for conflict in module.conflicts
            }
        )

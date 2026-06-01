from validator.validator import SemanticValidator


class ValidationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ValidationPass")
        SemanticValidator(module_registry=context.module_registry).validate(context.ast)
        context.resolved_modules = []
        seen_modules = set()
        if context.module_registry is None:
            return

        for package in context.ast.packages:
            module = context.module_registry.get(package.name)
            if module is None:
                continue
            module_key = module.name.lower()
            if module_key in seen_modules:
                continue
            seen_modules.add(module_key)
            context.resolved_modules.append(module)

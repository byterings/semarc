from semarc.architecture.stdlib.module_definition import ModuleDefinition
from semarc.architecture.stdlib.registry import ModuleRegistry


class ModuleDependencyError(Exception):
    def __init__(self, code: str, message: str, chain: list[str] | None = None) -> None:
        chain_text = "\n" + "\n-> ".join(chain) if chain else ""
        super().__init__(f"{code} {message}{chain_text}")
        self.code = code
        self.chain = chain or []


class ModuleDependencyResolver:
    """Resolves direct and recursive stdlib module dependencies."""

    def __init__(self, registry: ModuleRegistry) -> None:
        self.registry = registry

    def resolve(self, modules: list[ModuleDefinition]) -> list[ModuleDefinition]:
        resolved: list[ModuleDefinition] = []
        resolved_keys: set[str] = set()

        for module in modules:
            self._visit(module, [], resolved, resolved_keys)

        return resolved

    def _visit(
        self,
        module: ModuleDefinition,
        stack: list[str],
        resolved: list[ModuleDefinition],
        resolved_keys: set[str],
    ) -> None:
        module_key = module.name.lower()
        if module_key in [name.lower() for name in stack]:
            cycle_start = [name.lower() for name in stack].index(module_key)
            cycle = stack[cycle_start:] + [module.name]
            raise ModuleDependencyError("SEM6001", "Circular module dependency", cycle)

        if module_key not in resolved_keys:
            resolved.append(module)
            resolved_keys.add(module_key)

        stack.append(module.name)
        for dependency_name in module.dependencies:
            dependency = self.registry.get(dependency_name)
            if dependency is None:
                raise ModuleDependencyError(
                    "SEM6002",
                    f"Missing module dependency: {dependency_name}",
                    stack + [dependency_name],
                )
            self._visit(dependency, stack, resolved, resolved_keys)
        stack.pop()

from architecture.stdlib.module_definition import ModuleDefinition


class DuplicateModuleError(Exception):
    def __init__(self, module_name: str) -> None:
        super().__init__(f"SEM5002 Duplicate module: {module_name}")
        self.module_name = module_name


class ModuleRegistry:
    """Stores discovered stdlib modules by semantic module name."""

    def __init__(self) -> None:
        self._modules: dict[str, ModuleDefinition] = {}

    def register(self, module: ModuleDefinition) -> None:
        key = module.name.lower()
        if key in self._modules:
            raise DuplicateModuleError(module.name)
        self._modules[key] = module

    def get(self, name: str) -> ModuleDefinition | None:
        return self._modules.get(name.lower())

    def all(self) -> list[ModuleDefinition]:
        return [self._modules[name] for name in sorted(self._modules)]

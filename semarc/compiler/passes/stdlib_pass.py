from pathlib import Path

from semarc.architecture.stdlib import DuplicateModuleError, ModuleRegistry, StdlibLoader, StdlibLoadingError
from semarc.validator.validator import SemanticValidationError


class StdlibPass:
    """Loads stdlib module metadata before semantic validation."""

    def run(self, context) -> None:
        context.compiler_passes.append("StdlibPass")
        try:
            modules = StdlibLoader(self._stdlib_dir()).load_all()
            registry = ModuleRegistry()
            for module in modules:
                registry.register(module)
        except DuplicateModuleError as error:
            raise SemanticValidationError(f"[Semantic Error]\nSEM5002 Duplicate module: {error.module_name}") from error
        except StdlibLoadingError as error:
            raise SemanticValidationError(f"[Semantic Error]\n{error}") from error

        context.module_registry = registry
        context.loaded_modules = modules

    def _stdlib_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "stdlib"

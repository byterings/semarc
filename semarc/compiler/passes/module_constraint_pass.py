from semarc.architecture.stdlib import ModuleConstraintError, ModuleConstraintValidator
from semarc.validator.validator import SemanticValidationError


class ModuleConstraintPass:
    """Validates resolved modules against architecture-level requirements and conflicts."""

    def run(self, context) -> None:
        context.compiler_passes.append("ModuleConstraintPass")
        try:
            ModuleConstraintValidator().validate(context.ast, context.resolved_modules)
        except ModuleConstraintError as error:
            raise SemanticValidationError(f"[Semantic Error]\n{error}") from error

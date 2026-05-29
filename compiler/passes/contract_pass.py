from compiler.contracts import ContractValidator


class ContractPass:
    """Runs internal contract checks between architecture and generation."""

    def __init__(self) -> None:
        self.validator = ContractValidator()

    def validate_ast(self, context) -> None:
        context.compiler_passes.append("ContractPass:AST")
        self.validator.assert_valid("AST", self.validator.validate_ast(context.ast))

    def validate_ir(self, context) -> None:
        context.compiler_passes.append("ContractPass:IR")
        self.validator.assert_valid("IR", self.validator.validate_ir(context.ir))

    def validate_generation(self, context) -> None:
        context.compiler_passes.append("ContractPass:Generation")
        self.validator.assert_valid(
            "Generator",
            self.validator.validate_generator_result(context.generated_components),
        )

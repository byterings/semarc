from validator.validator import SemanticValidator


class ValidationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ValidationPass")
        SemanticValidator().validate(context.ast)

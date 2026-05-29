from parser.parser import Parser


class ParsingPass:
    def run(self, context) -> None:
        context.compiler_passes.append("ParsingPass")
        context.ast = Parser().parse(context.tokens)

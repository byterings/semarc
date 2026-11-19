from semarc.lexer.lexer import Lexer


class LexingPass:
    def run(self, context) -> None:
        context.compiler_passes.append("LexingPass")
        context.source = context.source_path.read_text(encoding="utf-8")
        context.tokens = Lexer().tokenize(context.source)

from compiler.diagnostics.diagnostic import DiagnosticError, DiagnosticWarning


class ConflictingAuthStrategiesRule:
    code = "AUTH002"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if not ast:
            return

        strategies = ast.metadata.get("auth_strategies", [])
        unique_strategies = sorted(set(strategies))
        if len(unique_strategies) > 1:
            result.add_error(
                DiagnosticError(
                    self.code,
                    "Conflicting authentication strategies detected.",
                    "AUTH",
                )
            )


class JwtRateLimitRule:
    code = "AUTH001"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if not ast or not ast.auth:
            return

        if ast.auth.strategy == "JWT":
            result.add_warning(
                DiagnosticWarning(
                    self.code,
                    "JWT authentication endpoints should use rate limiting.",
                    "AUTH JWT",
                )
            )

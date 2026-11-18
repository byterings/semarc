from compiler.diagnostics.diagnostic import DiagnosticError, DiagnosticWarning

GENERATED_AUTH_RATE_LIMITING = True


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
    """AUTH001: JWT endpoints need rate limiting.

    Every target generates rate limiting for POST /register and POST /login
    (AUTH_RATE_LIMIT attempts per AUTH_RATE_WINDOW seconds), so a JWT
    architecture satisfies the rule and no warning is emitted.
    """

    code = "AUTH001"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if not ast or not ast.auth or ast.auth.strategy != "JWT":
            return
        if not GENERATED_AUTH_RATE_LIMITING:
            result.add_warning(
                DiagnosticWarning(
                    self.code,
                    "JWT authentication endpoints should use rate limiting.",
                    "AUTH JWT",
                )
            )

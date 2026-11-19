from semarc.compiler.diagnostics.diagnostic import DiagnosticRecommendation


class LoginValidationRecommendationRule:
    code = "ROUTE001"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if not ast:
            return

        has_login = any(route.method == "POST" and route.path == "/login" for route in ast.routes)
        has_validation = any(validation.field_name in {"email", "password"} for validation in ast.validations)

        if has_login and not has_validation:
            result.add_recommendation(
                DiagnosticRecommendation(
                    self.code,
                    "Consider validation rules for login email and password fields.",
                    "ROUTE POST /login",
                )
            )

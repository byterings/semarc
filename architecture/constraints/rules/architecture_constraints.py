from compiler.diagnostics.diagnostic import DiagnosticRecommendation


class ArchitectureCompletenessRule:
    code = "ARCH001"

    def evaluate(self, context: dict, result) -> None:
        ir = context["ir"]
        if not ir:
            return

        repositories = ir.get("repositories", [])
        services = ir.get("services", [])
        if repositories and not any(service["name"] == "TokenService" for service in services):
            result.add_recommendation(
                DiagnosticRecommendation(
                    self.code,
                    "Repository pattern detected; consider service-layer orchestration for business workflows.",
                    "Architecture IR",
                )
            )

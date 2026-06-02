from compiler.diagnostics.diagnostic import DiagnosticRecommendation, DiagnosticWarning

from architecture.analysis.result import ArchitectureAnalysisResult
from architecture.analysis.rule import ArchitectureRule


class ArchitectureAnalyzer:
    """Evaluates deterministic architecture quality rules without changing compilation."""

    def __init__(self, rules: list[ArchitectureRule] | None = None) -> None:
        self.rules = rules or self._default_rules()

    def analyze(
        self,
        ast=None,
        loaded_profiles=None,
        resolved_modules=None,
        relationship_plan=None,
    ) -> ArchitectureAnalysisResult:
        result = ArchitectureAnalysisResult()
        context = {
            "ast": ast,
            "loaded_profiles": loaded_profiles or [],
            "resolved_modules": resolved_modules or [],
            "relationship_plan": relationship_plan or {},
        }

        for rule in self.rules:
            result.rules_executed += 1
            rule.evaluate(context, result)

        return result

    def _default_rules(self) -> list[ArchitectureRule]:
        return [
            ArchitectureRule(
                "SEM9001",
                "warning",
                "Public route without authentication",
                "Public route detected without authentication.",
                self._rule_public_route_without_authentication,
            ),
            ArchitectureRule(
                "SEM9002",
                "recommendation",
                "Payment module without audit logging",
                "Payment module detected without audit logging.",
                self._rule_payment_without_audit_logging,
            ),
            ArchitectureRule(
                "SEM9003",
                "warning",
                "Model appears unused",
                "Model appears unused by current route and relationship declarations.",
                self._rule_unused_model,
            ),
            ArchitectureRule(
                "SEM9004",
                "recommendation",
                "Ecommerce profile using SQLite",
                "Ecommerce profile is using SQLite.",
                self._rule_ecommerce_profile_with_sqlite,
            ),
            ArchitectureRule(
                "SEM9005",
                "recommendation",
                "Authentication loaded but no protected routes detected",
                "Authentication is configured but no protected routes were detected.",
                self._rule_auth_without_protected_routes,
            ),
        ]

    def _rule_public_route_without_authentication(self, context: dict, result: ArchitectureAnalysisResult) -> None:
        ast = context["ast"]
        if ast is None or self._has_authentication(ast, context["resolved_modules"]):
            return

        for route in ast.routes:
            if self._is_public_route(route.path):
                result.add_warning(
                    DiagnosticWarning(
                        "SEM9001",
                        f"Public route detected without authentication: {route.method} {route.path}",
                        f"route:{route.method} {route.path}",
                    )
                )

    def _rule_payment_without_audit_logging(self, context: dict, result: ArchitectureAnalysisResult) -> None:
        module_names = [module.name for module in context["resolved_modules"]]
        loaded = {name.lower() for name in module_names}
        if "audit.standard" in loaded:
            return

        for module_name in module_names:
            if module_name.lower().startswith("payment."):
                result.add_recommendation(
                    DiagnosticRecommendation(
                        "SEM9002",
                        f"Payment module loaded without audit logging: {module_name}",
                        f"module:{module_name}",
                    )
                )

    def _rule_unused_model(self, context: dict, result: ArchitectureAnalysisResult) -> None:
        ast = context["ast"]
        if ast is None:
            return

        related_models = {
            relation.source_model.lower() for relation in ast.relations
        } | {
            relation.target_model.lower() for relation in ast.relations
        }

        for model in ast.models:
            if self._model_is_used(model.name, ast.routes, related_models, ast.auth):
                continue
            result.add_warning(
                DiagnosticWarning(
                    "SEM9003",
                    f"Model appears unused: {model.name}",
                    f"model:{model.name}",
                )
            )

    def _rule_ecommerce_profile_with_sqlite(self, context: dict, result: ArchitectureAnalysisResult) -> None:
        ast = context["ast"]
        if ast is None or ast.database is None or ast.database.engine != "SQLITE":
            return

        for profile in context["loaded_profiles"]:
            if profile.name.lower() == "ecommerce":
                result.add_recommendation(
                    DiagnosticRecommendation(
                        "SEM9004",
                        "Ecommerce profile is using SQLITE; MYSQL is a stronger default for commerce workloads.",
                        f"profile:{profile.name}",
                    )
                )
                return

    def _rule_auth_without_protected_routes(self, context: dict, result: ArchitectureAnalysisResult) -> None:
        ast = context["ast"]
        if ast is None or not self._has_authentication(ast, context["resolved_modules"]):
            return

        if ast.routes and any(not self._is_auth_only_route(route.path) for route in ast.routes):
            return

        result.add_recommendation(
            DiagnosticRecommendation(
                "SEM9005",
                "Authentication is configured but no protected routes were detected.",
                "auth",
            )
        )

    def _has_authentication(self, ast, resolved_modules: list) -> bool:
        if getattr(ast, "auth", None) is not None:
            return True
        return any(module.name.lower().startswith("auth.") for module in resolved_modules)

    def _is_public_route(self, route_path: str) -> bool:
        return not self._is_auth_only_route(route_path)

    def _is_auth_only_route(self, route_path: str) -> bool:
        return route_path.lower() in {"/login"}

    def _model_is_used(self, model_name: str, routes: list, related_models: set[str], auth) -> bool:
        model_key = model_name.lower()
        if model_key in related_models:
            return True
        if auth is not None and model_key == "user":
            return True

        singular = self._segment_name(model_name)
        plural = self._pluralize(singular)
        tokens = {singular, plural}
        for route in routes:
            route_path = route.path.strip("/").lower()
            segments = [segment for segment in route_path.split("/") if segment]
            if tokens.intersection(segments):
                return True
        return False

    def _segment_name(self, model_name: str) -> str:
        output = []
        for index, char in enumerate(model_name):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output)

    def _pluralize(self, singular: str) -> str:
        if singular.endswith("y") and len(singular) > 1 and singular[-2] not in "aeiou":
            return singular[:-1] + "ies"
        if singular.endswith("s"):
            return singular
        return singular + "s"

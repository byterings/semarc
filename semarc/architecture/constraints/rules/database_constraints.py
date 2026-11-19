from semarc.compiler.diagnostics.diagnostic import DiagnosticRecommendation, DiagnosticWarning


class MissingDatabaseRule:
    code = "DB001"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if ast and ast.database is None:
            result.add_warning(
                DiagnosticWarning(
                    self.code,
                    "No database declaration found; generated persistence will be limited.",
                    "DATABASE",
                )
            )


class SqliteRedisRule:
    code = "DB002"

    def evaluate(self, context: dict, result) -> None:
        ast = context["ast"]
        if not ast or not ast.database:
            return

        cache = getattr(ast, "cache", None)
        cache_name = getattr(cache, "name", None)
        if ast.database.engine == "SQLITE" and cache_name == "REDIS":
            result.add_recommendation(
                DiagnosticRecommendation(
                    self.code,
                    "Redis cache may be unnecessary for lightweight SQLite deployments.",
                    "DATABASE SQLITE",
                )
            )

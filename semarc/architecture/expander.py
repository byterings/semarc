from semarc.ast_loader import load_semantic_nodes


nodes = load_semantic_nodes()
ArchitectureNode = nodes.ArchitectureNode


class ArchitectureExpander:
    """Expands semantic intent into language-neutral architecture components."""

    def expand(self, architecture: ArchitectureNode, plan: dict | None = None, target_profile: dict | None = None) -> dict:
        if plan is not None:
            return self._expand_plan(plan, target_profile)

        expanded = {
            "project": architecture.project.name,
            "target": architecture.target.name if architecture.target else "PHP",
            "target_profile": target_profile or {},
            "database": self._expand_database(architecture),
            "auth": None,
            "models": architecture.models,
            "repositories": [],
            "validators": [],
            "relationships": architecture.relations,
            "validations": architecture.validations,
            "profiles": architecture.profiles,
            "packages": architecture.packages,
            "routes": architecture.routes,
        }

        if architecture.auth and architecture.auth.strategy == "JWT":
            expanded["auth"] = {
                "strategy": "JWT",
                "controller": "AuthController",
                "services": ["TokenService", "PasswordHasher"],
                "middlewares": ["AuthMiddleware"],
                "features": ["token issuing", "token validation", "password hashing"],
            }
            expanded["validators"].append("Validator")

        for model in architecture.models:
            expanded["repositories"].append(f"{model.name}Repository")

        return expanded

    def _expand_plan(self, plan: dict, target_profile: dict | None) -> dict:
        return {
            "project": plan["project"],
            "target": plan["target"],
            "target_profile": target_profile or {},
            "database": plan["database"],
            "auth": plan["auth"],
            "models": plan["models"],
            "routes": plan["routes"],
            "repositories": plan["repositories"],
            "validators": plan["validators"],
            "relationships": plan["relationships"],
            "validations": plan["validations"],
            "profiles": plan.get("profiles", []),
            "packages": plan.get("packages", []),
        }

    def _expand_database(self, architecture: ArchitectureNode) -> dict:
        if architecture.database is None:
            return {"engine": "NONE"}
        return {"engine": architecture.database.engine}

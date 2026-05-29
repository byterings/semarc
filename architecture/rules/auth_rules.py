def apply_auth_rules(architecture, plan: dict, graph) -> None:
    if not architecture.auth:
        return

    if architecture.auth.strategy != "JWT":
        return

    plan["auth"] = {
        "meaning": "token-based authentication",
        "strategy": "JWT",
        "controller": "AuthController",
        "services": ["TokenService", "PasswordHasher"],
        "middlewares": ["AuthMiddleware"],
        "validators": ["Validator"],
        "features": ["token issuing", "token validation", "password hashing"],
    }
    plan["validators"].append("Validator")

    for component in ["AuthController", "AuthMiddleware", "TokenService", "PasswordHasher", "Validator"]:
        graph.add_node(component)

    graph.add_dependency("AuthController", "TokenService")
    graph.add_dependency("AuthController", "PasswordHasher")
    graph.add_dependency("AuthController", "Validator")
    graph.add_dependency("AuthMiddleware", "TokenService")
    graph.add_dependency("TokenService", "Validator")

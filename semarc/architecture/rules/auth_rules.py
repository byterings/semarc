AUTH_MODEL = "User"
AUTH_IDENTITY_FIELD = "email"
AUTH_SECRET_FIELD = "password"
AUTH_ROUTES = {
    ("POST", "/register"): "register",
    ("POST", "/login"): "login",
    ("GET", "/me"): "me",
    ("POST", "/token/refresh"): "refresh",
    ("POST", "/logout"): "logout",
    ("POST", "/me/password"): "change_password",
}
PASSWORD_RESET_ROUTES = {
    ("POST", "/password/forgot"): "forgot_password",
    ("POST", "/password/reset"): "reset_password",
}
EMAIL_VERIFICATION_ROUTES = {
    ("POST", "/email/verify"): "verify_email",
    ("POST", "/email/resend"): "resend_verification",
}
REFRESH_TOKEN_TABLE = "refresh_tokens"
REFRESH_TOKEN_TTL_SECONDS = 14 * 24 * 3600


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
    graph.add_dependency("AuthController", f"{AUTH_MODEL}Repository")
    graph.add_dependency("AuthMiddleware", "TokenService")
    graph.add_dependency("TokenService", "Validator")

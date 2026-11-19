AUTH_MODEL = "User"
# Strategies that create the User model, register/login routes and access policy.
# JWT sends a bearer token; SESSION a session cookie plus a CSRF header.
ACCOUNT_STRATEGIES = ("JWT", "SESSION")
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
OAUTH_MODULE_PREFIX = "auth.oauth."
OAUTH_TABLE = "oauth_accounts"
OAUTH_STATE_TTL_SECONDS = 600
# Authorization code flow endpoints and profile fields of each supported provider.
# A provider either reports the email and whether it is verified in the profile
# (verified_field), or lists addresses with their verification state (emails_url).
OAUTH_PROVIDERS = {
    "github": {
        "label": "GitHub",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "profile_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scopes": ["read:user", "user:email"],
        "subject_field": "id",
        "email_field": None,
        "verified_field": None,
        "name_field": "name",
    },
    "google": {
        "label": "Google",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "profile_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "emails_url": None,
        "scopes": ["openid", "email", "profile"],
        "subject_field": "sub",
        "email_field": "email",
        "verified_field": "email_verified",
        "name_field": "name",
    },
}
OAUTH_NAME_FIELD = "name"
REFRESH_TOKEN_TABLE = "refresh_tokens"
REFRESH_ROUTE = ("POST", "/token/refresh")
SESSION_TABLE = "sessions"
SESSION_TTL_SECONDS = 14 * 24 * 3600
SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
REFRESH_TOKEN_TTL_SECONDS = 14 * 24 * 3600


def apply_auth_rules(architecture, plan: dict, graph) -> None:
    if not architecture.auth:
        return

    strategy = architecture.auth.strategy
    if strategy not in ACCOUNT_STRATEGIES:
        return

    credential = "TokenService" if strategy == "JWT" else "SessionStore"
    plan["auth"] = {
        "meaning": "token-based authentication" if strategy == "JWT" else "cookie session authentication",
        "strategy": strategy,
        "controller": "AuthController",
        "services": [credential, "PasswordHasher"],
        "middlewares": ["AuthMiddleware"],
        "validators": ["Validator"],
        "features": ["token issuing", "token validation", "password hashing"]
        if strategy == "JWT"
        else ["session cookies", "CSRF protection", "password hashing"],
    }
    plan["validators"].append("Validator")

    for component in ["AuthController", "AuthMiddleware", credential, "PasswordHasher", "Validator"]:
        graph.add_node(component)

    graph.add_dependency("AuthController", credential)
    graph.add_dependency("AuthController", "PasswordHasher")
    graph.add_dependency("AuthController", "Validator")
    graph.add_dependency("AuthController", f"{AUTH_MODEL}Repository")
    graph.add_dependency("AuthMiddleware", credential)
    graph.add_dependency(credential, "Validator")

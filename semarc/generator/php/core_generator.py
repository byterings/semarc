from semarc.generator.php.base import PhpFileWriter
from semarc.generator.utils.resource_views import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


CORE_FILES = [
    "Env",
    "HttpException",
    "Request",
    "Response",
    "Cors",
    "Router",
    "Cast",
    "Database",
    "Schema",
    "Migrator",
    "Repository",
    "ResourceService",
    "HomePage",
]


class CoreGenerator:
    """Writes the small runtime the generated project is built on."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for name in CORE_FILES:
            values = {"default_limit": DEFAULT_PAGE_SIZE, "max_limit": MAX_PAGE_SIZE} if name == "ResourceService" else {}
            self.writer.render(f"core/{name}.php", f"core/{name}.php.tpl", values)
            files.append(f"core/{name}.php")

        self.writer.render("validators/Validator.php", "core/Validator.php.tpl")
        files.append("validators/Validator.php")
        return files

    def generate_auth(self, ir: dict) -> dict[str, list[str]]:
        auth = ir["auth"]
        values = {
            "auth_model": auth["model"],
            "identity_field": auth["identity_field"],
            "secret_field": auth["secret_field"],
            "token_ttl": auth["token_ttl_seconds"],
            "attempts": auth["rate_limit"]["attempts"],
            "window": auth["rate_limit"]["window_seconds"],
        }
        self.writer.render("core/Jwt.php", "auth/Jwt.php.tpl")
        self.writer.render("core/RateLimiter.php", "auth/RateLimiter.php.tpl", values)
        self.writer.render("services/TokenService.php", "auth/TokenService.php.tpl", values)
        self.writer.render("services/PasswordHasher.php", "auth/PasswordHasher.php.tpl")
        self.writer.render("middleware/AuthMiddleware.php", "auth/AuthMiddleware.php.tpl", values)
        self.writer.render("controllers/AuthController.php", "auth/AuthController.php.tpl", values)
        return {
            "core": ["core/Jwt.php", "core/RateLimiter.php", "services/TokenService.php", "services/PasswordHasher.php"],
            "middleware": ["middleware/AuthMiddleware.php"],
            "controllers": ["controllers/AuthController.php"],
        }

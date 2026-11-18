from semarc.generator.php.base import PHP_HEADER, PhpFileWriter
from semarc.generator.php.php_syntax import php_literal
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
            "register_extra": self._bootstrap_admin(auth),
        }
        self.writer.render("core/Jwt.php", "auth/Jwt.php.tpl")
        self.writer.render("core/RateLimiter.php", "auth/RateLimiter.php.tpl", values)
        self.writer.render(
            "core/RefreshTokens.php",
            "auth/RefreshTokens.php.tpl",
            {"table": auth["features"]["refresh_tokens"]["table"], "ttl": auth["features"]["refresh_tokens"]["ttl_seconds"]},
        )
        self.writer.render("services/TokenService.php", "auth/TokenService.php.tpl", values)
        self.writer.render("services/PasswordHasher.php", "auth/PasswordHasher.php.tpl")
        self.writer.render("middleware/AuthMiddleware.php", "auth/AuthMiddleware.php.tpl", values)
        self.writer.render("controllers/AuthController.php", "auth/AuthController.php.tpl", values)
        controllers = ["controllers/AuthController.php"]
        roles = auth["features"]["roles"]
        if roles:
            self.writer.write("controllers/RoleController.php", self._role_controller(auth, roles), "php role controller")
            controllers.append("controllers/RoleController.php")
        return {
            "core": ["core/Jwt.php", "core/RateLimiter.php", "core/RefreshTokens.php", "services/TokenService.php", "services/PasswordHasher.php"],
            "middleware": ["middleware/AuthMiddleware.php"],
            "controllers": controllers,
        }

    def _bootstrap_admin(self, auth: dict) -> str:
        roles = auth["features"]["roles"]
        if not roles:
            return ""
        identity = auth["identity_field"]
        return "\n".join(
            [
                "        $bootstrap = Env::get('BOOTSTRAP_ADMIN_EMAIL');",
                f"        if ($bootstrap !== null && strcasecmp((string) $user['{identity}'], $bootstrap) === 0) {{",
                f"            $this->repository->update($user['id'], ['role' => '{roles['admin']}']);",
                "            $user = $this->users->get($user['id']);",
                "        }",
                "",
            ]
        )

    def _role_controller(self, auth: dict, roles: dict) -> str:
        model = auth["model"]
        return "\n".join(
            [
                PHP_HEADER,
                "/** Admins change user roles: PUT /users/{id}/role {\"role\": \"...\"} */",
                "final class RoleController",
                "{",
                f"    public const ROLES = {php_literal(roles['names'])};",
                "",
                f"    private {model}Repository $repository;",
                f"    private {model}Service $users;",
                "",
                "    public function __construct()",
                "    {",
                f"        $this->repository = new {model}Repository();",
                f"        $this->users = new {model}Service();",
                "    }",
                "",
                "    /**",
                "     * @return array<string, mixed>",
                "     */",
                "    public function update(Request $request, string $id): array",
                "    {",
                "        $role = $request->json()['role'] ?? null;",
                "        if (!is_string($role) || !in_array($role, self::ROLES, true)) {",
                "            throw HttpException::validation(['role' => ['role must be one of: ' . implode(', ', self::ROLES)]]);",
                "        }",
                "        $userId = preg_match('/^[1-9]\\d{0,17}$/', $id) === 1 ? (int) $id : 0;",
                "        if ($userId === 0 || $this->repository->findById($userId) === null) {",
                f"            throw HttpException::notFound(\"{model} {{$id}} not found.\");",
                "        }",
                "        $this->repository->update($userId, ['role' => $role]);",
                "",
                "        return ['data' => $this->users->get($userId)];",
                "    }",
                "}",
                "",
            ]
        )

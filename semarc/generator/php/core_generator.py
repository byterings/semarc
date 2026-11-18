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
            "register_extra": self._bootstrap_admin(auth) + self._send_verification(auth),
            "extra_methods": self._mail_methods(auth),
        }
        self.writer.render("core/Jwt.php", "auth/Jwt.php.tpl")
        self.writer.render("core/RateLimiter.php", "auth/RateLimiter.php.tpl", values)
        mail_sources = []
        if auth["features"]["password_reset"] or auth["features"]["email_verification"]:
            self.writer.render("core/Mailer.php", "auth/Mailer.php.tpl")
            self.writer.render("core/OneTimeTokens.php", "auth/OneTimeTokens.php.tpl")
            mail_sources = ["core/Mailer.php", "core/OneTimeTokens.php"]
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
            "core": ["core/Jwt.php", "core/RateLimiter.php", "core/RefreshTokens.php", *mail_sources, "services/TokenService.php", "services/PasswordHasher.php"],
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

    def _send_verification(self, auth: dict) -> str:
        if not auth["features"]["email_verification"]:
            return ""
        return "        $this->sendVerification($user);\n"

    def _mail_methods(self, auth: dict) -> str:
        identity, secret = auth["identity_field"], auth["secret_field"]
        methods = []
        reset = auth["features"]["password_reset"]
        if reset:
            methods.append(
                "\n".join(
                    [
                        "",
                        "    public function forgotPassword(Request $request): Response",
                        "    {",
                        "        RateLimiter::forAuth()->hit('forgot|' . $request->ip);",
                        f"        $email = self::requiredString($request->json(), '{identity}');",
                        f"        $record = $this->repository->findBy('{identity}', $email);",
                        "        if ($record !== null) {",
                        f"            $token = (new OneTimeTokens('{reset['table']}'))->issue((int) $record['id'], {reset['ttl_seconds']});",
                        "            (new Mailer())->send($email, 'Reset your password', self::mailBody(",
                        "                'Use this token to reset your password.',",
                        "                $token,",
                        "                'reset-password',",
                        f"                'The token expires in {reset['ttl_seconds'] // 60} minutes. If you did not ask for a reset, ignore this email.',",
                        "            ));",
                        "        }",
                        "",
                        "        return Response::json(['data' => ['message' => 'If the account exists, a reset email has been sent.']], 202);",
                        "    }",
                        "",
                        "    public function resetPassword(Request $request): Response",
                        "    {",
                        "        $input = $request->json();",
                        "        $token = self::requiredString($input, 'token');",
                        f"        $password = self::validatedPassword($input['{secret}'] ?? null, '{secret}');",
                        f"        $userId = (new OneTimeTokens('{reset['table']}'))->consume($token)",
                        "            ?? throw HttpException::validation(['token' => ['token is invalid or expired']]);",
                        f"        $this->repository->update($userId, ['{secret}' => $this->hasher->hash($password)]);",
                        "        $this->refreshTokens->revokeAll($userId);",
                        "",
                        "        return Response::noContent();",
                        "    }",
                    ]
                )
            )
        verification = auth["features"]["email_verification"]
        if verification:
            methods.append(
                "\n".join(
                    [
                        "",
                        "    /**",
                        "     * @return array<string, mixed>",
                        "     */",
                        "    public function verifyEmail(Request $request): array",
                        "    {",
                        f"        $userId = (new OneTimeTokens('{verification['table']}'))->consume(self::requiredString($request->json(), 'token'))",
                        "            ?? throw HttpException::validation(['token' => ['token is invalid or expired']]);",
                        f"        $this->repository->update($userId, ['{verification['field']}' => Database::now()]);",
                        "",
                        "        return ['data' => $this->users->get($userId)];",
                        "    }",
                        "",
                        "    public function resendVerification(Request $request): Response",
                        "    {",
                        "        $record = $this->repository->findById((int) $request->userId);",
                        f"        if ($record !== null && $record['{verification['field']}'] === null) {{",
                        "            $this->sendVerification($record);",
                        "        }",
                        "",
                        "        return Response::json(['data' => ['message' => 'A verification email is sent when the address is not verified yet.']], 202);",
                        "    }",
                        "",
                        "    /**",
                        "     * @param array<string, mixed> $user",
                        "     */",
                        "    private function sendVerification(array $user): void",
                        "    {",
                        f"        $token = (new OneTimeTokens('{verification['table']}'))->issue((int) $user['id'], {verification['ttl_seconds']});",
                        f"        (new Mailer())->send((string) $user['{identity}'], 'Verify your email address', self::mailBody(",
                        "            'Use this token to confirm your email address.',",
                        "            $token,",
                        "            'verify-email',",
                        f"            'The token expires in {verification['ttl_seconds'] // 3600} hours.',",
                        "        ));",
                        "    }",
                    ]
                )
            )
        if methods:
            methods.append(
                "\n".join(
                    [
                        "",
                        "    private static function mailBody(string $intro, string $token, string $page, string $footer): string",
                        "    {",
                        "        $lines = [$intro, '', 'Token: ' . $token];",
                        "        $appUrl = Env::get('APP_URL');",
                        "        if ($appUrl !== null) {",
                        "            $lines[] = 'Link: ' . rtrim($appUrl, '/') . '/' . $page . '?token=' . $token;",
                        "        }",
                        "",
                        "        return implode(\"\\n\", [...$lines, '', $footer]) . \"\\n\";",
                        "    }",
                    ]
                )
            )
        return "\n".join(methods) + ("\n" if methods else "")

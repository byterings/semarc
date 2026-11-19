from semarc.generator.php.base import PHP_HEADER, PhpFileWriter
from semarc.generator.utils.resource_views import secret_fields


class ServiceGenerator:
    """Maps IR business components to services built on ResourceService."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for model in ir["models"]:
            path = f"services/{model['name']}Service.php"
            self.writer.write(path, self._service(model), "php service")
            files.append(path)
        return files

    def _service(self, model: dict) -> str:
        name = model["name"]
        secrets = secret_fields(model)
        lines = [
            PHP_HEADER,
            f"final class {name}Service extends ResourceService",
            "{",
        ]
        if secrets:
            lines.extend(["    private PasswordHasher $hasher;", ""])
        lines.extend(
            [
                "    public function __construct()",
                "    {",
                f"        parent::__construct(new {name}Repository(), {name}::class);",
            ]
        )
        if secrets:
            lines.append("        $this->hasher = new PasswordHasher();")
        lines.append("    }")

        if secrets:
            lines.extend(
                [
                    "",
                    "    protected function beforeWrite(array $data): array",
                    "    {",
                ]
            )
            for secret in secrets:
                lines.extend(
                    [
                        f"        if (isset($data['{secret}'])) {{",
                        f"            $data['{secret}'] = $this->hasher->hash($data['{secret}']);",
                        "        }",
                    ]
                )
            lines.extend(["", "        return $data;", "    }"])

        lines.extend(["}", ""])
        return "\n".join(lines)

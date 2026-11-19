from semarc.generator.php.base import PHP_HEADER, PhpFileWriter


class RepositoryGenerator:
    """Maps IR persistence components to PDO repositories."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for model in ir["models"]:
            name = model["name"]
            path = f"repositories/{name}Repository.php"
            content = "\n".join(
                [
                    PHP_HEADER,
                    f"final class {name}Repository extends Repository",
                    "{",
                    "    public function __construct()",
                    "    {",
                    f"        parent::__construct({name}::TABLE);",
                    "    }",
                    "}",
                    "",
                ]
            )
            self.writer.write(path, content, "php repository")
            files.append(path)
        return files

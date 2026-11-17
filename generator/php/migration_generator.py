from generator.php.base import PHP_HEADER, PhpFileWriter
from generator.php.php_syntax import php_literal


class MigrationGenerator:
    """Maps the ordered IR migration plan to driver-neutral PHP table definitions."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for table in ir["migrations"]["tables"]:
            definition = {
                "table": table["table"],
                "columns": [
                    {
                        "name": column["name"],
                        "type": column["type"],
                        "required": column["required"],
                        "unique": column["unique"],
                    }
                    for column in table["fields"]
                ],
                "foreign_keys": [
                    {
                        "column": foreign_key["column"],
                        "references": foreign_key["references_table"],
                        "unique": foreign_key.get("unique", False),
                    }
                    for foreign_key in table["foreign_keys"]
                ],
            }
            path = f"migrations/{table['sequence']:03d}_create_{table['table']}_table.php"
            self.writer.write(path, f"{PHP_HEADER}\nreturn {php_literal(definition)};\n", "php migration")
            files.append(path)
        return files

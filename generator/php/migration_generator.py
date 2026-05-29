from pathlib import Path

from generator.php.template_engine import TemplateEngine


class MigrationGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        migrations_dir = self.output_dir / "migrations"
        migrations_dir.mkdir(parents=True, exist_ok=True)

        for table in ir.get("migrations", {}).get("tables", []):
            sql_template = "migrations/create_table.sql.tpl"
            sql = self.template_engine.render(
                sql_template,
                {
                    "table_name": table["table"],
                    "columns": self._columns(table),
                    "foreign_keys": self._foreign_keys(table),
                },
            )
            sql_path = migrations_dir / f"create_{table['table']}_table.sql"
            sql_path.write_text(sql, encoding="utf-8")
            self._report(sql_path, sql_template)

            class_template = "migrations/migration_class.tpl"
            class_name = "Create" + "".join(part.title() for part in table["table"].split("_")) + "Table"
            class_content = self.template_engine.render(
                class_template,
                {
                    "class_name": class_name,
                    "sql": sql.rstrip(),
                },
            )
            class_path = migrations_dir / f"{class_name}.php"
            class_path.write_text(class_content, encoding="utf-8")
            self._report(class_path, class_template)

    def _columns(self, table: dict) -> str:
        lines = []
        for field in table["fields"]:
            lines.append(f"    {field['name']} {self._sql_type(field['type'])} NOT NULL,")
        return "\n".join(lines)

    def _foreign_keys(self, table: dict) -> str:
        lines = []
        for foreign_key in table["foreign_keys"]:
            lines.append(f"    {foreign_key['column']} INT NOT NULL,")
            lines.append(f"    INDEX idx_{foreign_key['column']} ({foreign_key['column']}),")
            lines.append(
                "    FOREIGN KEY "
                f"({foreign_key['column']}) REFERENCES "
                f"{foreign_key['references_table']}({foreign_key['references_column']}),"
            )
        return "\n".join(lines)

    def _sql_type(self, semantic_type: str) -> str:
        return {
            "STRING": "VARCHAR(255)",
            "TEXT": "TEXT",
            "INTEGER": "INT",
            "BOOLEAN": "BOOLEAN",
            "FLOAT": "FLOAT",
        }.get(semantic_type, "VARCHAR(255)")

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

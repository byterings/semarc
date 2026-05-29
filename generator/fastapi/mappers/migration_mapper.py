class MigrationMapper:
    """Maps language-neutral migration metadata into FastAPI SQLAlchemy tables."""

    def map(self, ir: dict) -> list[dict]:
        mapped = []

        for table in ir.get("migrations", {}).get("tables", []):
            mapped.append(
                {
                    "path": f"migrations/create_{table['table']}_table.py",
                    "template": "migrations/table.tpl",
                    "values": {
                        "table_name": table["table"],
                        "columns": self._columns(table),
                        "foreign_keys": self._foreign_keys(table),
                    },
                }
            )

        return mapped

    def _columns(self, table: dict) -> str:
        return "\n".join(
            f'    Column("{field["name"]}", {self._column_type(field["type"])}),'
            for field in table["fields"]
        )

    def _foreign_keys(self, table: dict) -> str:
        return "\n".join(
            "    Column("
            f'"{foreign_key["column"]}", '
            f'Integer, ForeignKey("{foreign_key["references_table"]}.{foreign_key["references_column"]}")'
            "),"
            for foreign_key in table["foreign_keys"]
        )

    def _column_type(self, semantic_type: str) -> str:
        return {
            "STRING": "String",
            "TEXT": "String",
            "INTEGER": "Integer",
            "BOOLEAN": "Integer",
            "FLOAT": "Integer",
        }.get(semantic_type, "String")

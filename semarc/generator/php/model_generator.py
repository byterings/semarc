from semarc.generator.php.base import PHP_HEADER, PhpFileWriter
from semarc.generator.php.php_syntax import php_literal
from semarc.generator.utils.resource_views import field_rules, output_fields, secret_fields, unique_columns


CASTS = {
    "STRING": "string",
    "TEXT": "string",
    "INTEGER": "int",
    "FLOAT": "float",
    "BOOLEAN": "bool",
    "DATE": "date",
    "DATETIME": "timestamp",
}


class ModelGenerator:
    """Maps IR entities to PHP model classes holding field metadata and casting."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for model in ir["models"]:
            path = f"models/{model['name']}.php"
            self.writer.write(path, self._model(model), "php model")
            files.append(path)
        return files

    def _model(self, model: dict) -> str:
        fields = {
            model_field["name"]: {key: value for key, value in field_rules(model_field).items() if key not in {"unique", "secret"}}
            for model_field in model["fields"]
        }
        references = {
            reference["column"]: {
                "model": reference["model"],
                "table": reference["table"],
                "owner": reference["owner"],
            }
            for reference in model["references"]
        }
        relation_comments = [
            f"// Relation metadata: {relation['source']} {relation['type']} {relation['target']}"
            for relation in model["relations"]
        ]
        casts = "\n".join(
            f"            '{name}' => Cast::{CASTS[field_type]}($row['{name}']),"
            for name, field_type in output_fields(model)
        )

        lines = [PHP_HEADER]
        if relation_comments:
            lines.extend(relation_comments + [""])
        lines.extend(
            [
                f"final class {model['name']}",
                "{",
                f"    public const TABLE = '{model['table']}';",
                "",
                "    /** Declared fields and their validation rules. */",
                f"    public const FIELDS = {php_literal(fields, 4)};",
                "",
                "    /** Foreign key columns and the model they reference. */",
                f"    public const REFERENCES = {php_literal(references, 4)};",
                "",
                "    /** Tables whose rows reference this model; deletes are refused while they exist. */",
                f"    public const DEPENDENTS = {php_literal(model['dependents'], 4)};",
                "",
                f"    public const UNIQUE = {php_literal(unique_columns(model))};",
                "",
                f"    public const HIDDEN = {php_literal(secret_fields(model))};",
                "",
                "    /** Query parameters list routes accept as equality filters, with their types. */",
                f"    public const FILTERS = {php_literal(model['query']['filters'])};",
                "",
                "    /** Fields list routes can sort by (?sort=field or ?sort=-field). */",
                f"    public const SORT = {php_literal(model['query']['sort'])};",
                "",
                "    /**",
                "     * @return array<string, array<string, mixed>>",
                "     */",
                "    public static function inputRules(?string $excludeColumn = null): array",
                "    {",
                "        $rules = self::FIELDS;",
                "        foreach (self::REFERENCES as $column => $reference) {",
                "            if ($column !== $excludeColumn) {",
                "                $rules[$column] = ['type' => 'INTEGER', 'required' => true, 'not_empty' => false, 'email' => false, 'min' => 1, 'max' => null];",
                "            }",
                "        }",
                "",
                "        return $rules;",
                "    }",
                "",
                "    /**",
                "     * @param array<string, mixed> $row",
                "     * @return array<string, mixed>",
                "     */",
                "    public static function toArray(array $row): array",
                "    {",
                "        return [",
                casts,
                "        ];",
                "    }",
                "}",
                "",
            ]
        )
        return "\n".join(lines)

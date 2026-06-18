from pathlib import Path

from generator.php.template_engine import TemplateEngine
from generator.utils.inflector import camel_case, pluralize


class ModelGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        models_dir = self.output_dir / "models"
        models_dir.mkdir(parents=True, exist_ok=True)

        for model in ir["models"]:
            properties = []
            assignments = []
            relationship_properties = []
            relationships = []

            for field in model["fields"]:
                php_type = self._php_type(field["type"])
                name = field["name"]
                properties.append(f"    public {php_type} ${name};")
                assignments.append(f"        $this->{name} = $data['{name}'] ?? '';")

            for foreign_key in model.get("foreign_keys", []):
                name = foreign_key["column"]
                properties.append(f"    public int ${name};")
                assignments.append(f"        $this->{name} = $data['{name}'] ?? 0;")

            for relation in model.get("relations", []):
                relationship_properties.append(
                    f"    // Relation metadata: {relation['source']} {relation['type']} {relation['target']}"
                )

            template = "model.tpl"
            content = self.template_engine.render(
                template,
                {
                    "model_name": model["name"],
                    "properties": "\n".join(properties),
                    "relationship_properties": "\n".join(relationship_properties),
                    "assignments": "\n".join(assignments),
                    "relationships": "\n\n".join(relationships),
                },
            )
            path = models_dir / f"{model['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _php_type(self, semantic_type: str) -> str:
        return {
            "STRING": "string",
            "TEXT": "string",
            "INTEGER": "int",
            "BOOLEAN": "bool",
            "FLOAT": "float",
        }.get(semantic_type, "string")

    def _plural_method(self, model_name: str) -> str:
        return camel_case(pluralize(model_name))

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

from pathlib import Path

from generator.php.template_engine import TemplateEngine


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
                if relation["source"] == model["name"] and relation["type"] == "HAS_MANY":
                    method = self._plural_method(relation["target"])
                    relationships.append(
                        "\n".join(
                            [
                                f"    public function {method}()",
                                "    {",
                                f"        return $this->hasMany({relation['target']}::class);",
                                "    }",
                            ]
                        )
                    )
                elif relation["source"] == model["name"] and relation["type"] == "HAS_ONE":
                    method = relation["target"][0].lower() + relation["target"][1:]
                    relationships.append(
                        "\n".join(
                            [
                                f"    public function {method}()",
                                "    {",
                                f"        return $this->hasOne({relation['target']}::class);",
                                "    }",
                            ]
                        )
                    )
                elif relation["target"] == model["name"] and relation["type"] in {"HAS_MANY", "HAS_ONE"}:
                    method = relation["source"][0].lower() + relation["source"][1:]
                    relationships.append(
                        "\n".join(
                            [
                                f"    public function {method}()",
                                "    {",
                                f"        return $this->belongsTo({relation['source']}::class);",
                                "    }",
                            ]
                        )
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
        method = model_name[0].lower() + model_name[1:]
        if method.endswith("s"):
            return method
        return method + "s"

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

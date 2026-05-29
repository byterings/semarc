class RelationshipEngine:
    """Builds relationship graph and migration plan from semantic relations."""

    def build(self, architecture) -> dict:
        models = {model.name: model for model in architecture.models}
        relationships = [self._relationship(relation) for relation in architecture.relations]
        foreign_keys = [self._foreign_key(relation) for relation in relationships]

        return {
            "graph": self._graph(models, relationships),
            "relationships": relationships,
            "foreign_keys": foreign_keys,
            "migrations": self._migrations(models, foreign_keys),
        }

    def _relationship(self, relation) -> dict:
        return {
            "source": relation.source_model,
            "type": relation.relation_type,
            "target": relation.target_model,
        }

    def _foreign_key(self, relation: dict) -> dict:
        if relation["type"] in {"HAS_MANY", "HAS_ONE"}:
            parent = relation["source"]
            child = relation["target"]
        else:
            parent = relation["target"]
            child = relation["source"]

        return {
            "table": self._table_name(child),
            "column": f"{self._snake_case(parent)}_id",
            "references_table": self._table_name(parent),
            "references_column": "id",
            "source_model": parent,
            "target_model": child,
        }

    def _graph(self, models: dict, relationships: list[dict]) -> dict:
        graph = {name: [] for name in sorted(models)}

        for relation in relationships:
            graph.setdefault(relation["source"], []).append(
                {
                    "type": relation["type"],
                    "model": relation["target"],
                }
            )
            if relation["type"] == "BELONGS_TO":
                graph.setdefault(relation["target"], [])

        return graph

    def _migrations(self, models: dict, foreign_keys: list[dict]) -> dict:
        return {
            "tables": [
                {
                    "model": model.name,
                    "table": self._table_name(model.name),
                    "fields": [
                        {
                            "name": field.name,
                            "type": field.field_type,
                        }
                        for field in model.fields
                    ],
                    "foreign_keys": [
                        foreign_key
                        for foreign_key in foreign_keys
                        if foreign_key["table"] == self._table_name(model.name)
                    ],
                }
                for model in models.values()
            ],
            "foreign_keys": foreign_keys,
        }

    def _table_name(self, model_name: str) -> str:
        return f"{self._snake_case(model_name)}s"

    def _snake_case(self, value: str) -> str:
        output = []
        for index, char in enumerate(value):
            if char.isupper() and index > 0:
                output.append("_")
            output.append(char.lower())
        return "".join(output)

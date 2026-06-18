from generator.fastapi.mappers.name_utils import python_type, snake_case
from generator.utils.inflector import pluralize


class ModelMapper:
    """Maps IR models into Pydantic schemas and SQLAlchemy-style models."""

    def map(self, ir: dict) -> list[dict]:
        mapped = []

        for model in ir["models"]:
            schema_fields = []
            orm_fields = [
                "    id = Column(Integer, primary_key=True, index=True)",
            ]

            for field in model["fields"]:
                schema_fields.append(f"    {field['name']}: {python_type(field['type'])}")
                orm_fields.append(f"    {field['name']} = Column(String)")

            for relation in model["relations"]:
                schema_fields.append(
                    f"    # Relation metadata: {relation['source']} {relation['type']} {relation['target']}"
                )

            mapped.append(
                {
                    "path": f"schemas/{snake_case(model['name'])}.py",
                    "template": "schemas/schema.tpl",
                    "values": {
                        "schema_name": model["name"],
                    "fields": "\n".join(schema_fields) if schema_fields else "    pass",
                    },
                }
            )
            mapped.append(
                {
                    "path": f"models/{snake_case(model['name'])}.py",
                    "template": "model.tpl",
                    "values": {
                        "model_name": model["name"],
                        "fields": "\n".join(orm_fields),
                    },
                }
            )

        return mapped

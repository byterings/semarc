from generator.fastapi.mappers.name_utils import python_type, snake_case


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
                if relation["source"] == model["name"] and relation["type"] == "HAS_MANY":
                    schema_fields.append(f"    {snake_case(relation['target'])}s: list = []")
                    orm_fields.append(
                        f"    {snake_case(relation['target'])}s = relationship('{relation['target']}', back_populates='{snake_case(relation['source'])}')"
                    )
                if relation["target"] == model["name"] and relation["type"] == "HAS_MANY":
                    source_table = f"{snake_case(relation['source'])}s"
                    source_name = snake_case(relation["source"])
                    orm_fields.append(f"    {source_name}_id = Column(Integer, ForeignKey('{source_table}.id'))")
                    orm_fields.append(
                        f"    {source_name} = relationship('{relation['source']}', back_populates='{snake_case(relation['target'])}s')"
                    )
                if relation["source"] == model["name"] and relation["type"] == "BELONGS_TO":
                    target_table = f"{snake_case(relation['target'])}s"
                    target_name = snake_case(relation["target"])
                    orm_fields.append(f"    {target_name}_id = Column(Integer, ForeignKey('{target_table}.id'))")
                    orm_fields.append(
                        f"    {target_name} = relationship('{relation['target']}')"
                    )
                if relation["source"] == model["name"] and relation["type"] == "HAS_ONE":
                    orm_fields.append(
                        f"    {snake_case(relation['target'])} = relationship('{relation['target']}', uselist=False)"
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

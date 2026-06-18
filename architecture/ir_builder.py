from generator.utils.inflector import pluralize, snake_case


class ArchitectureIRBuilder:
    """Builds the implementation IR consumed by target-language generators."""

    def build(self, expanded_architecture: dict) -> dict:
        ir = {
            "project": expanded_architecture["project"],
            "target": expanded_architecture.get("target", "PHP"),
            "target_profile": expanded_architecture.get("target_profile", {}),
            "config": {
                "database": expanded_architecture["database"],
            },
            "controllers": [],
            "services": [],
            "models": [],
            "middlewares": [],
            "repositories": [],
            "validators": [],
            "relationships": [],
            "foreign_keys": [],
            "migrations": {},
            "profiles": [
                {
                    "name": profile.name,
                    "metadata": dict(profile.metadata),
                }
                for profile in expanded_architecture.get("profiles", [])
            ],
            "packages": [
                {
                    "name": package.name,
                    "metadata": dict(package.metadata),
                }
                for package in expanded_architecture.get("packages", [])
            ],
            "modules": expanded_architecture.get("modules", []),
            "routes": [],
        }

        auth = expanded_architecture.get("auth")
        if auth:
            ir["controllers"].append(
                {
                    "name": auth["controller"],
                    "type": "auth",
                    "strategy": auth["strategy"],
                }
            )
            ir["services"].extend({"name": service, "type": "auth"} for service in auth["services"])
            ir["middlewares"].extend(
                {"name": middleware, "type": "auth", "strategy": auth["strategy"]}
                for middleware in auth["middlewares"]
            )

        for model in expanded_architecture["models"]:
            ir["models"].append(
                {
                    "name": model.name,
                    "fields": [
                        {"name": field.name, "type": field.field_type}
                        for field in model.fields
                    ],
                    "relations": self._relations_for(model.name, expanded_architecture["relationships"]),
                    "foreign_keys": self._foreign_keys_for(
                        model.name,
                        expanded_architecture.get("migration_plan", {}).get("foreign_keys", []),
                    ),
                }
            )

        for repository in expanded_architecture["repositories"]:
            model_name = repository.removesuffix("Repository")
            ir["repositories"].append(
                {
                    "name": repository,
                    "model": model_name,
                    "type": "memory",
                    "dependencies": self._repository_dependencies(
                        model_name,
                        expanded_architecture["relationships"],
                    ),
                }
            )

        for validator in expanded_architecture["validators"]:
            ir["validators"].append(
                {
                    "name": validator,
                    "type": "input",
                    "rules": ["required", "email", "min"],
                }
            )

        for validation in expanded_architecture["validations"]:
            ir["validators"].append(
                {
                    "name": "Validator",
                    "type": "input",
                    "field": validation.field_name,
                    "rules": validation.rules,
                }
            )

        ir["relationships"] = [
            {
                "source": relationship["source"] if isinstance(relationship, dict) else relationship.source_model,
                "type": relationship["type"] if isinstance(relationship, dict) else relationship.relation_type,
                "target": relationship["target"] if isinstance(relationship, dict) else relationship.target_model,
            }
            for relationship in expanded_architecture["relationships"]
        ]
        ir["foreign_keys"] = expanded_architecture.get("migration_plan", {}).get("foreign_keys", [])
        ir["migrations"] = expanded_architecture.get("migration_plan", {})

        for route in expanded_architecture["routes"]:
            ir["routes"].append(
                {
                    "method": route.method,
                    "path": route.path,
                    "handler": self._handler_for(route),
                }
            )

        return ir

    def _handler_for(self, route) -> dict:
        if route.method == "POST" and route.path == "/login":
            return {
                "type": "controller",
                "component": "AuthController",
                "action": "login",
            }
        if route.method == "GET":
            return {"type": "json", "payload": "data"}
        return {"type": "json", "payload": "message"}

    def _relations_for(self, model_name: str, relationships: list) -> list[dict]:
        model_relations = []
        for relationship in relationships:
            source = relationship["source"] if isinstance(relationship, dict) else relationship.source_model
            target = relationship["target"] if isinstance(relationship, dict) else relationship.target_model
            relation_type = relationship["type"] if isinstance(relationship, dict) else relationship.relation_type
            if source == model_name or target == model_name:
                model_relations.append(
                    {
                        "source": source,
                        "type": relation_type,
                        "target": target,
                    }
                )
        return model_relations

    def _foreign_keys_for(self, model_name: str, foreign_keys: list[dict]) -> list[dict]:
        table_name = self._table_name(model_name)
        return [foreign_key for foreign_key in foreign_keys if foreign_key["table"] == table_name]

    def _repository_dependencies(self, model_name: str, relationships: list) -> list[str]:
        dependencies = set()
        for relationship in relationships:
            source = relationship["source"] if isinstance(relationship, dict) else relationship.source_model
            target = relationship["target"] if isinstance(relationship, dict) else relationship.target_model
            relation_type = relationship["type"] if isinstance(relationship, dict) else relationship.relation_type

            if source == model_name and relation_type in {"HAS_MANY", "HAS_ONE"}:
                dependencies.add(f"{target}Repository")
            if target == model_name and relation_type == "BELONGS_TO":
                dependencies.add(f"{source}Repository")

        return sorted(dependencies)

    def _table_name(self, model_name: str) -> str:
        return pluralize(snake_case(model_name))

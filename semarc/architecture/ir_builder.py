class ArchitectureIRBuilder:
    """Builds the implementation IR consumed by target-language generators."""

    def build(self, expanded_architecture: dict) -> dict:
        resource_plan = expanded_architecture["resource_plan"]
        foreign_keys = expanded_architecture.get("migration_plan", {}).get("foreign_keys", [])
        relationships = [
            {
                "source": relationship["source"] if isinstance(relationship, dict) else relationship.source_model,
                "type": relationship["type"] if isinstance(relationship, dict) else relationship.relation_type,
                "target": relationship["target"] if isinstance(relationship, dict) else relationship.target_model,
            }
            for relationship in expanded_architecture["relationships"]
        ]

        ir = {
            "project": expanded_architecture["project"],
            "target": expanded_architecture.get("target", "PHP"),
            "target_profile": expanded_architecture.get("target_profile", {}),
            "config": {
                "database": expanded_architecture["database"],
            },
            "auth": resource_plan["auth"],
            "controllers": [],
            "services": [],
            "models": [],
            "middlewares": [],
            "repositories": [],
            "validators": [],
            "relationships": relationships,
            "foreign_keys": foreign_keys,
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

        for model in resource_plan["models"]:
            ir["models"].append(
                {
                    "name": model["name"],
                    "table": model["table"],
                    "resource": model["resource"],
                    "origin": model["origin"],
                    "fields": [dict(model_field) for model_field in model["fields"]],
                    "relations": self._relations_for(model["name"], relationships),
                    "foreign_keys": [
                        foreign_key for foreign_key in foreign_keys if foreign_key["table"] == model["table"]
                    ],
                    "references": [dict(reference) for reference in model["references"]],
                    "dependents": [dict(dependent) for dependent in model["dependents"]],
                    "query": {"filters": dict(model["query"]["filters"]), "sort": list(model["query"]["sort"])},
                }
            )
            ir["repositories"].append(
                {
                    "name": f"{model['name']}Repository",
                    "model": model["name"],
                    "type": "sql",
                    "dependencies": self._repository_dependencies(model["name"], relationships),
                }
            )

        for validator in expanded_architecture["validators"]:
            ir["validators"].append(
                {
                    "name": validator,
                    "type": "input",
                    "rules": ["required", "email", "min", "max"],
                }
            )

        for validation in expanded_architecture["validations"]:
            ir["validators"].append(
                {
                    "name": "Validator",
                    "type": "input",
                    "model": validation.model_name,
                    "field": validation.field_name,
                    "rules": validation.rules,
                    "parameters": dict(validation.parameters),
                    **({"values": list(validation.values)} if validation.values else {}),
                }
            )

        ir["migrations"] = {
            "tables": [
                {
                    "model": model["name"],
                    "table": model["table"],
                    "fields": [
                        {
                            "name": model_field["name"],
                            "type": model_field["type"],
                            "required": model_field["required"],
                            "unique": model_field["unique"],
                            "index": model_field.get("index", False),
                        }
                        for model_field in model["fields"]
                    ],
                    "foreign_keys": [
                        foreign_key for foreign_key in foreign_keys if foreign_key["table"] == model["table"]
                    ],
                }
                for model in resource_plan["models"]
            ]
            + [dict(table) for table in resource_plan.get("internal_tables", [])],
            "foreign_keys": foreign_keys,
        }

        for route in resource_plan["routes"]:
            ir["routes"].append(
                {
                    "method": route["method"],
                    "path": route["path"],
                    "origin": route["origin"],
                    "access": route["access"],
                    "parameters": list(route["parameters"]),
                    "roles": list(route.get("roles", [])),
                    "operation": dict(route["operation"]),
                    "handler": self._handler_for(route["operation"]),
                }
            )

        return ir

    def _handler_for(self, operation: dict) -> dict:
        kind = operation["kind"]
        if kind.startswith("auth_"):
            return {
                "type": "controller",
                "component": "AuthController",
                "action": kind.removeprefix("auth_"),
            }
        if operation.get("model"):
            return {
                "type": "controller",
                "component": f"{operation['model']}Controller",
                "action": kind,
            }
        return {"type": "todo", "action": "custom"}

    def _relations_for(self, model_name: str, relationships: list[dict]) -> list[dict]:
        return [
            dict(relationship)
            for relationship in relationships
            if relationship["source"] == model_name or relationship["target"] == model_name
        ]

    def _repository_dependencies(self, model_name: str, relationships: list[dict]) -> list[str]:
        dependencies = set()
        for relationship in relationships:
            if relationship["source"] == model_name and relationship["type"] in {"HAS_MANY", "HAS_ONE"}:
                dependencies.add(f"{relationship['target']}Repository")
            if relationship["target"] == model_name and relationship["type"] == "BELONGS_TO":
                dependencies.add(f"{relationship['source']}Repository")
        return sorted(dependencies)

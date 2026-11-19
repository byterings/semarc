from semarc.architecture.contracts.generation_contract import (
    API_LAYER,
    AUTH_LAYER,
    BUSINESS_LAYER,
    CONFIGURATION_LAYER,
    ENTITY_LAYER,
    PERSISTENCE_LAYER,
    PROJECT_LAYER,
    ContractComponent,
    GenerationContract,
)


class ContractDefinition:
    """Builds a framework-neutral generation contract from Architecture IR."""

    def build(self, ir: dict) -> GenerationContract:
        contract = GenerationContract(
            project_name=ir["project"],
            target=ir.get("target", "PHP"),
        )
        contract.add_component(
            ContractComponent(
                "project:application",
                PROJECT_LAYER,
                ir["project"],
                {"target": ir.get("target", "PHP")},
            )
        )

        database = ir.get("config", {}).get("database")
        if database:
            contract.add_component(
                ContractComponent(
                    "configuration:database",
                    CONFIGURATION_LAYER,
                    "Database",
                    {"engine": database.get("engine", "")},
                )
            )

        for model in ir.get("models", []):
            model_name = model["name"]
            entity_id = f"entity:{model_name}"
            persistence_id = f"persistence:{model_name}Repository"
            business_id = f"business:{model_name}Service"

            contract.add_component(
                ContractComponent(entity_id, ENTITY_LAYER, model_name, {"model": model_name})
            )
            contract.add_component(
                ContractComponent(
                    persistence_id,
                    PERSISTENCE_LAYER,
                    f"{model_name}Repository",
                    {"model": model_name},
                )
            )
            contract.add_component(
                ContractComponent(
                    business_id,
                    BUSINESS_LAYER,
                    f"{model_name}Service",
                    {"model": model_name},
                )
            )
            contract.add_dependency(persistence_id, entity_id, "persistence stores entity")
            contract.add_dependency(business_id, persistence_id, "business uses persistence")
            if database:
                contract.add_dependency(persistence_id, "configuration:database", "persistence uses database config")

        if ir.get("controllers") or ir.get("middlewares") or ir.get("services"):
            auth_components = [
                component
                for component in ir.get("controllers", []) + ir.get("middlewares", []) + ir.get("services", [])
                if component.get("type") == "auth"
            ]
            if auth_components:
                contract.add_component(
                    ContractComponent(
                        "auth:authentication",
                        AUTH_LAYER,
                        "Authentication",
                        {"strategy": auth_components[0].get("strategy", "JWT")},
                    )
                )

        for route in ir.get("routes", []):
            operation = route.get("operation", {})
            kind = operation.get("kind", "custom")
            is_auth = kind.startswith("auth_")
            model_name = None if is_auth else operation.get("model")
            route_id = f"api:{route['method']}:{route['path']}"
            route_component = contract.add_component(
                ContractComponent(
                    route_id,
                    API_LAYER,
                    f"{route['method']} {route['path']}",
                    {
                        "method": route["method"],
                        "path": route["path"],
                        "model": model_name,
                        "operation": kind,
                        "access": route.get("access", "public"),
                        "auth": is_auth,
                        "todo": kind == "custom",
                    },
                )
            )

            if (is_auth or route.get("access") == "protected") and "auth:authentication" in contract.components:
                contract.add_dependency(route_component.component_id, "auth:authentication", "api uses auth layer")
            if model_name and kind != "custom":
                contract.add_dependency(route_component.component_id, f"business:{model_name}Service", "api uses business layer")

        for relationship in ir.get("relationships", []):
            source_repository = f"persistence:{relationship['source']}Repository"
            target_repository = f"persistence:{relationship['target']}Repository"
            if source_repository in contract.components and target_repository in contract.components:
                contract.add_dependency(source_repository, target_repository, "relationship persistence dependency")

        return contract

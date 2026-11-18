from semarc.architecture.contracts.generation_contract import (
    API_LAYER,
    AUTH_LAYER,
    BUSINESS_LAYER,
    CONFIGURATION_LAYER,
    ENTITY_LAYER,
    PERSISTENCE_LAYER,
    PROJECT_LAYER,
)


class TargetContractAdapter:
    """Maps neutral contract layers to target implementation concepts."""

    TARGET_MAPPINGS = {
        "php": {
            PROJECT_LAYER: "project files",
            CONFIGURATION_LAYER: "config files",
            ENTITY_LAYER: "models",
            PERSISTENCE_LAYER: "repositories",
            BUSINESS_LAYER: "services",
            API_LAYER: "controllers and routes",
            AUTH_LAYER: "auth services and middleware",
        },
        "fastapi": {
            PROJECT_LAYER: "project files",
            CONFIGURATION_LAYER: "settings",
            ENTITY_LAYER: "models and schemas",
            PERSISTENCE_LAYER: "repositories",
            BUSINESS_LAYER: "services",
            API_LAYER: "routers",
            AUTH_LAYER: "auth dependencies and middleware",
        },
        "nestjs": {
            PROJECT_LAYER: "project files",
            CONFIGURATION_LAYER: "module configuration",
            ENTITY_LAYER: "entities",
            PERSISTENCE_LAYER: "repositories",
            BUSINESS_LAYER: "services",
            API_LAYER: "controllers",
            AUTH_LAYER: "guards and auth module",
        },
    }

    def map(self, contract, target_definition) -> dict:
        target = target_definition.generator
        mapping = self.TARGET_MAPPINGS.get(target, {})
        return {
            "target": target,
            "layers": {
                layer: mapping.get(layer, "unsupported")
                for layer in contract.required_layers()
            },
        }

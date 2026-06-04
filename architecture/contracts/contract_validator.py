from architecture.contracts.contract_error import ContractError
from architecture.contracts.generation_contract import API_LAYER, BUSINESS_LAYER, PERSISTENCE_LAYER


class ContractValidator:
    """Validates framework-neutral generation contract integrity."""

    def validate(self, contract, target_definition) -> None:
        errors = []
        errors.extend(self._validate_capabilities(contract, target_definition))
        errors.extend(self._validate_dependencies(contract))
        errors.extend(self._validate_layer_wiring(contract))
        errors.extend(self._validate_duplicate_routes(contract))

        if errors:
            raise ContractError("\n".join(f"- {error}" for error in errors))

    def _validate_capabilities(self, contract, target_definition) -> list[str]:
        errors = []
        capabilities = target_definition.capabilities
        for layer in contract.required_layers():
            if not capabilities.supports(layer):
                errors.append(f"Target {target_definition.name} does not support required {layer} layer")
        return errors

    def _validate_dependencies(self, contract) -> list[str]:
        errors = []
        for dependency in contract.dependencies:
            if dependency.source not in contract.components:
                errors.append(f"Dependency source does not exist: {dependency.source}")
            if dependency.target not in contract.components:
                errors.append(f"Dependency target does not exist: {dependency.target}")
        return errors

    def _validate_layer_wiring(self, contract) -> list[str]:
        errors = []
        for component in contract.components.values():
            dependency_layers = {
                contract.components[dependency].layer
                for dependency in component.dependencies
                if dependency in contract.components
            }
            if component.layer == API_LAYER and component.metadata.get("path") != "/login" and not component.metadata.get("todo"):
                if BUSINESS_LAYER not in dependency_layers:
                    errors.append(f"API component has no business dependency: {component.name}")
            if component.layer == BUSINESS_LAYER and PERSISTENCE_LAYER not in dependency_layers:
                errors.append(f"Business component has no persistence dependency: {component.name}")
            if component.layer == PERSISTENCE_LAYER:
                has_entity_dependency = any(
                    contract.components[dependency].layer == "entity"
                    for dependency in component.dependencies
                    if dependency in contract.components
                )
                if not has_entity_dependency:
                    errors.append(f"Persistence component has no entity dependency: {component.name}")
        return errors

    def _validate_duplicate_routes(self, contract) -> list[str]:
        routes = []
        for component in contract.components_for_layer(API_LAYER):
            method = component.metadata.get("method")
            path = component.metadata.get("path")
            if method and path:
                routes.append((method, path))
        duplicates = sorted({route for route in routes if routes.count(route) > 1})
        return [f"Duplicate API route: {method} {path}" for method, path in duplicates]

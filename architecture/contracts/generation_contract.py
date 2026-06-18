from dataclasses import dataclass, field


PROJECT_LAYER = "project"
CONFIGURATION_LAYER = "configuration"
ENTITY_LAYER = "entity"
PERSISTENCE_LAYER = "persistence"
BUSINESS_LAYER = "business"
API_LAYER = "api"
AUTH_LAYER = "auth"

ARCHITECTURE_LAYERS = [
    PROJECT_LAYER,
    CONFIGURATION_LAYER,
    ENTITY_LAYER,
    PERSISTENCE_LAYER,
    BUSINESS_LAYER,
    API_LAYER,
    AUTH_LAYER,
]


@dataclass(frozen=True)
class ContractDependency:
    source: str
    target: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "reason": self.reason,
        }


@dataclass
class ContractComponent:
    component_id: str
    layer: str
    name: str
    metadata: dict = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)

    def add_dependency(self, dependency_id: str) -> None:
        if dependency_id not in self.dependencies:
            self.dependencies.append(dependency_id)

    def to_dict(self) -> dict:
        return {
            "id": self.component_id,
            "layer": self.layer,
            "name": self.name,
            "metadata": dict(self.metadata),
            "dependencies": list(self.dependencies),
        }


class GenerationContract:
    """Framework-neutral generation contract derived from Architecture IR."""

    def __init__(self, project_name: str, target: str) -> None:
        self.project_name = project_name
        self.target = target
        self.components: dict[str, ContractComponent] = {}
        self.dependencies: list[ContractDependency] = []

    def add_component(self, component: ContractComponent) -> ContractComponent:
        if component.component_id in self.components:
            return self.components[component.component_id]
        self.components[component.component_id] = component
        return component

    def add_dependency(self, source_id: str, target_id: str, reason: str) -> None:
        source = self.components[source_id]
        if target_id not in self.components:
            return
        source.add_dependency(target_id)
        dependency = ContractDependency(source_id, target_id, reason)
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def components_for_layer(self, layer: str) -> list[ContractComponent]:
        return [
            component
            for component in self.components.values()
            if component.layer == layer
        ]

    def required_layers(self) -> list[str]:
        layers = {component.layer for component in self.components.values()}
        return [layer for layer in ARCHITECTURE_LAYERS if layer in layers]

    def to_dict(self) -> dict:
        return {
            "project": self.project_name,
            "target": self.target,
            "layers": self.required_layers(),
            "components": [
                self.components[component_id].to_dict()
                for component_id in sorted(self.components)
            ],
            "dependencies": [
                dependency.to_dict()
                for dependency in sorted(
                    self.dependencies,
                    key=lambda item: (item.source, item.target, item.reason),
                )
            ],
        }

class DependencyGraphError(Exception):
    pass


class DependencyGraph:
    """Tracks architecture component dependencies in a deterministic graph."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.dependencies: dict[str, set[str]] = {}
        self.duplicate_dependencies: set[tuple[str, str]] = set()

    def add_node(self, name: str) -> None:
        self.nodes.add(name)
        self.dependencies.setdefault(name, set())

    def add_dependency(self, component: str, dependency: str) -> None:
        self.add_node(component)
        self.add_node(dependency)
        if dependency in self.dependencies[component]:
            self.duplicate_dependencies.add((component, dependency))
        self.dependencies[component].add(dependency)

    def validate(self) -> None:
        errors = []
        missing = []
        for component, dependencies in self.dependencies.items():
            for dependency in dependencies:
                if dependency not in self.nodes:
                    missing.append(f"{component} depends on missing {dependency}")

        if missing:
            errors.extend(missing)

        if self.duplicate_dependencies:
            errors.extend(
                f"Duplicate dependency: {component} -> {dependency}"
                for component, dependency in sorted(self.duplicate_dependencies)
            )

        try:
            self.traverse()
        except DependencyGraphError as error:
            errors.append(str(error))

        if errors:
            raise DependencyGraphError("\n".join(errors))

    def traverse(self) -> list[str]:
        visited = set()
        ordered = []

        for node in sorted(self.nodes):
            self._visit(node, visited, set(), ordered)

        return ordered

    def to_debug(self) -> dict:
        diagnostics = self.diagnostics()
        return {
            "nodes": sorted(self.nodes),
            "dependencies": {
                component: sorted(dependencies)
                for component, dependencies in sorted(self.dependencies.items())
            },
            "order": self.traverse(),
            "diagnostics": diagnostics,
        }

    def diagnostics(self) -> dict:
        depended_on = {
            dependency
            for dependencies in self.dependencies.values()
            for dependency in dependencies
        }
        orphan_nodes = [
            node
            for node in sorted(self.nodes)
            if not self.dependencies.get(node) and node not in depended_on
        ]
        root_nodes = [
            node
            for node in sorted(self.nodes)
            if node not in depended_on
        ]
        return {
            "duplicate_dependencies": [
                {"component": component, "dependency": dependency}
                for component, dependency in sorted(self.duplicate_dependencies)
            ],
            "orphan_nodes": orphan_nodes,
            "root_nodes": root_nodes,
            "node_count": len(self.nodes),
            "dependency_count": sum(len(dependencies) for dependencies in self.dependencies.values()),
        }

    def _visit(self, node: str, visited: set[str], stack: set[str], ordered: list[str]) -> None:
        if node in visited:
            return
        if node in stack:
            raise DependencyGraphError(f"Dependency cycle detected at {node}")

        stack.add(node)
        for dependency in sorted(self.dependencies.get(node, set())):
            self._visit(dependency, visited, stack, ordered)
        stack.remove(node)
        visited.add(node)
        ordered.append(node)

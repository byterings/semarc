import heapq


class ArchitectureOptimizer:
    """Deterministic IR cleanup that preserves semantic meaning."""

    COMPONENT_LISTS = ["controllers", "services", "middlewares"]

    def optimize(self, ir: dict) -> dict:
        ir["models"] = sorted(ir["models"], key=lambda model: model["name"])
        ir["repositories"] = sorted(ir["repositories"], key=lambda repo: repo["name"])
        ir["relationships"] = sorted(
            ir["relationships"],
            key=lambda relation: (relation["source"], relation["type"], relation["target"]),
        )
        for key in self.COMPONENT_LISTS:
            ir[key] = self.unique_by_name(ir.get(key, []))
        ir["validators"] = self.unique_exact(ir.get("validators", []))
        ir["migrations"] = self.order_migrations(ir.get("migrations", {}))
        return ir

    def unique_by_name(self, components: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for component in components:
            if component["name"] in seen:
                continue
            seen.add(component["name"])
            unique.append(component)
        return unique

    def unique_exact(self, components: list[dict]) -> list[dict]:
        unique = []
        for component in components:
            if component not in unique:
                unique.append(component)
        return unique

    def order_migrations(self, migrations: dict) -> dict:
        tables = migrations.get("tables", [])
        by_name = {table["table"]: table for table in tables}
        dependencies = {
            table["table"]: sorted(
                {
                    foreign_key["references_table"]
                    for foreign_key in table.get("foreign_keys", [])
                    if foreign_key["references_table"] in by_name
                    and foreign_key["references_table"] != table["table"]
                }
            )
            for table in tables
        }

        ordered_names = self._topological_order(dependencies)
        ordered_tables = [
            {**by_name[name], "sequence": index}
            for index, name in enumerate(ordered_names, start=1)
        ]
        return {**migrations, "tables": ordered_tables}

    def _topological_order(self, dependencies: dict[str, list[str]]) -> list[str]:
        remaining = {name: set(required) for name, required in dependencies.items()}
        dependents: dict[str, set[str]] = {name: set() for name in dependencies}
        for name, required in dependencies.items():
            for dependency in required:
                dependents[dependency].add(name)

        ready = [name for name, required in remaining.items() if not required]
        heapq.heapify(ready)
        ordered = []
        while ready:
            name = heapq.heappop(ready)
            ordered.append(name)
            for dependent in sorted(dependents[name]):
                remaining[dependent].discard(name)
                if not remaining[dependent]:
                    heapq.heappush(ready, dependent)

        if len(ordered) != len(dependencies):
            cyclic = sorted(set(dependencies) - set(ordered))
            raise ValueError("Circular foreign key dependency between tables: " + ", ".join(cyclic))
        return ordered

from architecture.packages.package import Package


class PackageRegistry:
    """Stores semantic package metadata without applying compiler behavior."""

    def __init__(self) -> None:
        self._packages: dict[str, Package] = {}

    def register(self, package: Package) -> None:
        self._packages[package.name.lower()] = package

    def get(self, name: str) -> Package | None:
        return self._packages.get(name.lower())

    def all(self) -> list[Package]:
        return [self._packages[name] for name in sorted(self._packages)]

from pathlib import Path

from architecture.packages.package import Package
from architecture.packages.registry import PackageRegistry


class PackageLoader:
    """Loads stdlib package metadata for future semantic modules."""

    def __init__(self, stdlib_dir: str | Path = "stdlib") -> None:
        self.stdlib_dir = Path(stdlib_dir)

    def load_all(self) -> PackageRegistry:
        registry = PackageRegistry()
        if not self.stdlib_dir.exists():
            return registry

        for package_file in sorted(self.stdlib_dir.rglob("package.meta")):
            registry.register(self.load(package_file))
        return registry

    def load(self, path: str | Path) -> Package:
        path = Path(path)
        metadata = self._read_metadata(path)
        domain = metadata.pop("domain", path.parent.name)
        name = metadata.pop("name", domain)
        dependencies = self._split_list(metadata.pop("dependencies", ""))
        description = metadata.pop("description", "")
        return Package(
            name=name,
            domain=domain,
            description=description,
            dependencies=dependencies,
            metadata=metadata,
        )

    def _read_metadata(self, path: Path) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip()
        return metadata

    def _split_list(self, value: str) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

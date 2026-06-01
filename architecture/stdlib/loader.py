from pathlib import Path

from architecture.stdlib.module_definition import ModuleDefinition


class StdlibLoadingError(Exception):
    def __init__(self, code: str, message: str, source: Path | None = None) -> None:
        source_text = f"\nSource: {source}" if source else ""
        super().__init__(f"{code} {message}{source_text}")
        self.code = code
        self.source = source


class StdlibLoader:
    """Discovers metadata-only stdlib modules from module.yaml files."""

    REQUIRED_FIELDS = {"name", "version", "description"}

    def __init__(self, stdlib_dir: str | Path = "stdlib") -> None:
        self.stdlib_dir = Path(stdlib_dir)

    def load_all(self) -> list[ModuleDefinition]:
        if not self.stdlib_dir.exists():
            return []

        try:
            module_files = sorted(self.stdlib_dir.rglob("module.yaml"))
        except OSError as error:
            raise StdlibLoadingError("SEM5004", f"Stdlib loading failed: {error}", self.stdlib_dir) from error

        return [self.load(path) for path in module_files]

    def load(self, path: str | Path) -> ModuleDefinition:
        path = Path(path)
        try:
            metadata = self._read_yaml_subset(path)
        except OSError as error:
            raise StdlibLoadingError("SEM5004", f"Stdlib loading failed: {error}", path) from error

        missing = sorted(self.REQUIRED_FIELDS - set(metadata))
        if missing:
            raise StdlibLoadingError(
                "SEM5003",
                "Invalid module definition; missing fields: " + ", ".join(missing),
                path,
            )

        return ModuleDefinition(
            name=metadata["name"],
            version=metadata["version"],
            description=metadata["description"],
            source_path=path,
        )

    def _read_yaml_subset(self, path: Path) -> dict[str, str]:
        metadata: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise StdlibLoadingError("SEM5003", "Invalid module definition line", path)
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip("\"'")
        return metadata

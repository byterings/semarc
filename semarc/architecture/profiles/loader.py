from pathlib import Path

from semarc.architecture.profiles.profile import Profile
from semarc.architecture.profiles.registry import ProfileRegistry


class ProfileLoadingError(Exception):
    def __init__(self, code: str, message: str, source: Path | None = None) -> None:
        source_text = f"\nSource: {source}" if source else ""
        super().__init__(f"{code} {message}{source_text}")
        self.code = code
        self.source = source


class ProfileLoader:
    """Loads simple key/value profile metadata for future profile passes."""

    def __init__(self, profiles_dir: str | Path = Path(__file__).resolve().parents[2] / "profiles") -> None:
        self.profiles_dir = Path(profiles_dir)

    def load_all(self) -> ProfileRegistry:
        registry = ProfileRegistry()
        if not self.profiles_dir.exists():
            return registry

        for path in sorted(self.profiles_dir.glob("*.profile")):
            registry.register(self.load(path))
        return registry

    def load(self, path: str | Path) -> Profile:
        path = Path(path)
        metadata = self._read_metadata(path)
        name = metadata.pop("name", path.stem)
        packages = self._split_list(metadata.pop("packages", ""))
        extends = self._split_list(metadata.pop("extends", ""))
        modules = metadata.pop("modules", [])
        if not isinstance(modules, list) or not all(isinstance(item, str) and item for item in modules):
            raise ProfileLoadingError("SEM8003", "Invalid profile definition", path)
        description = metadata.pop("description", "")
        return Profile(
            name=name,
            description=description,
            extends=extends,
            modules=modules,
            packages=packages,
            metadata=metadata,
        )

    def _read_metadata(self, path: Path) -> dict:
        metadata: dict = {}
        packages = []
        modules = []
        current_list_key = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("- ", "* ")):
                if current_list_key != "modules":
                    raise ProfileLoadingError("SEM8003", "Invalid profile definition", path)
                item = line[2:].strip().strip("\"'")
                if not item:
                    raise ProfileLoadingError("SEM8003", "Invalid profile definition", path)
                modules.append(item)
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                current_list_key = None
                if key == "packages":
                    packages.extend(self._split_list(value))
                elif key == "modules":
                    if value:
                        raise ProfileLoadingError("SEM8003", "Invalid profile definition", path)
                    current_list_key = "modules"
                else:
                    metadata[key] = value
                continue

            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            command, value = parts[0].upper(), parts[1].strip()
            if command == "PROFILE":
                metadata["name"] = value
            elif command == "EXTENDS":
                existing = metadata.get("extends", "")
                metadata["extends"] = ", ".join(item for item in [existing, value] if item)
            elif command == "USE":
                packages.append(value)
                modules.append(value)

        if packages:
            metadata["packages"] = ", ".join(packages)
        metadata["modules"] = modules
        return metadata

    def _split_list(self, value: str) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

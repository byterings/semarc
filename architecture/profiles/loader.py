from pathlib import Path

from architecture.profiles.profile import Profile
from architecture.profiles.registry import ProfileRegistry


class ProfileLoader:
    """Loads simple key/value profile metadata for future profile passes."""

    def __init__(self, profiles_dir: str | Path = "profiles") -> None:
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
        extends = metadata.pop("extends", None)
        if extends == "":
            extends = None
        description = metadata.pop("description", "")
        return Profile(
            name=name,
            description=description,
            extends=extends,
            packages=packages,
            metadata=metadata,
        )

    def _read_metadata(self, path: Path) -> dict[str, str]:
        metadata: dict[str, str] = {}
        packages = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "packages":
                    packages.extend(self._split_list(value))
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
                metadata["extends"] = value
            elif command == "USE":
                packages.append(value)

        if packages:
            metadata["packages"] = ", ".join(packages)
        return metadata

    def _split_list(self, value: str) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

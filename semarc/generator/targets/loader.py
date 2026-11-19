from pathlib import Path

from semarc.generator.targets.target import TargetMetadata


class TargetLoader:
    """Loads target metadata files for future target package support."""

    REQUIRED_FIELDS = {"name", "language", "description"}

    def load(self, path: str | Path) -> TargetMetadata:
        path = Path(path)
        metadata = self._read_metadata(path)
        missing = sorted(self.REQUIRED_FIELDS - set(metadata))
        if missing:
            raise ValueError("Invalid target metadata; missing fields: " + ", ".join(missing))
        return TargetMetadata(
            name=metadata["name"],
            language=metadata["language"],
            description=metadata["description"],
            generator=metadata.get("generator", metadata["name"]),
            supports=tuple(metadata.get("supports", [])),
            source_path=path,
        )

    def _read_metadata(self, path: Path) -> dict:
        values = {}
        current_list_key = None
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("-") and current_list_key:
                values.setdefault(current_list_key, []).append(stripped[1:].strip().strip("\"'"))
                continue
            current_list_key = None
            line = stripped
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Invalid target metadata line: {line}")
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if value == "":
                values[key] = []
                current_list_key = key
            else:
                values[key] = value
        return values

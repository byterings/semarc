from pathlib import Path

from generator.targets.target import TargetMetadata


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
            source_path=path,
        )

    def _read_metadata(self, path: Path) -> dict[str, str]:
        values = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                raise ValueError(f"Invalid target metadata line: {line}")
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip("\"'")
        return values

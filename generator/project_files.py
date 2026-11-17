import json
from pathlib import Path

from compiler.version import SEMARC_VERSION


class ProjectFileWriter:
    """Writes the generator manifest shared by every target."""

    def __init__(self, output_dir: Path, reporter=None) -> None:
        self.output_dir = output_dir
        self.reporter = reporter

    def write_text(self, relative_path: str, content: str, template: str) -> None:
        path = self.output_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if self.reporter:
            self.reporter(path, template)

    def write_manifest(self, ir: dict, target: str, profiles: list | None = None, modules: list | None = None) -> None:
        manifest = {
            "generator": target,
            "semarc_version": SEMARC_VERSION,
            "project": ir.get("project", ""),
            "generated_at": "1970-01-01T00:00:00Z",
            "profiles": profiles if profiles is not None else ir.get("profiles_loaded", []),
            "modules": modules if modules is not None else [module["name"] for module in ir.get("modules", [])],
        }
        self.write_text(
            "generator_manifest.json",
            json.dumps(manifest, indent=2) + "\n",
            "generator manifest",
        )

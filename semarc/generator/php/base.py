from pathlib import Path


class PhpFileWriter:
    """Writes generated PHP project files and records them for contract checks."""

    def __init__(self, output_dir: Path, template_engine, reporter) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def write(self, relative_path: str, content: str, template: str) -> None:
        path = self.output_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        self.reporter(path, template)

    def render(self, relative_path: str, template: str, values: dict | None = None) -> None:
        self.write(relative_path, self.template_engine.render(template, values), template)


PHP_HEADER = "<?php\n\ndeclare(strict_types=1);\n"

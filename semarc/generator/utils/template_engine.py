from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "templates"


class TemplateEngine:
    """Very small deterministic template renderer using {{placeholders}}."""

    def __init__(self, template_dir: str = "php") -> None:
        name = template_dir.removeprefix("templates/")
        self.template_dir = TEMPLATE_ROOT / name

    def render(self, template_name: str, values: dict[str, object] | None = None) -> str:
        template = (self.template_dir / template_name).read_text(encoding="utf-8")
        for key, value in (values or {}).items():
            template = template.replace("{{" + key + "}}", str(value))
        if "{{" in template:
            start = template.index("{{")
            raise ValueError(f"Unresolved placeholder in {template_name}: {template[start:start + 40]}")
        return template

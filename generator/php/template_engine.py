from pathlib import Path


class TemplateEngine:
    """Very small deterministic template renderer using {{placeholders}}."""

    TEMPLATE_ROOT = Path(__file__).resolve().parents[2]

    def __init__(self, template_dir: str = "templates/php") -> None:
        self.template_dir = self.TEMPLATE_ROOT / template_dir

    def render(self, template_name: str, values: dict[str, object]) -> str:
        template = (self.template_dir / template_name).read_text(encoding="utf-8")
        for key, value in values.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template

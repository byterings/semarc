from pathlib import Path


class TemplateEngine:
    """Very small deterministic template renderer using {{placeholders}}."""

    def __init__(self, template_dir: str = "templates/php") -> None:
        self.template_dir = Path(template_dir)

    def render(self, template_name: str, values: dict[str, object]) -> str:
        template = (self.template_dir / template_name).read_text(encoding="utf-8")
        for key, value in values.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template

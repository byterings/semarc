from pathlib import Path

from generator.php.template_engine import TemplateEngine


class ValidatorGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        validators_dir = self.output_dir / "validators"
        validators_dir.mkdir(parents=True, exist_ok=True)

        for validator in self._unique_validators(ir):
            template = "validators/validator.tpl"
            content = self.template_engine.render(
                template,
                {
                    "class_name": validator["name"],
                },
            )
            path = validators_dir / f"{validator['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _unique_validators(self, ir: dict) -> list[dict]:
        validators = {}
        for validator in ir["validators"]:
            validators[validator["name"]] = validator
        return [validators[name] for name in sorted(validators)]

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

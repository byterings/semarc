from pathlib import Path

from generator.php.template_engine import TemplateEngine


class AuthGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        self._generate_controllers(ir)
        self._generate_services(ir)
        self._generate_middlewares(ir)

    def _generate_controllers(self, ir: dict) -> None:
        controllers_dir = self.output_dir / "controllers"
        controllers_dir.mkdir(parents=True, exist_ok=True)

        for controller in ir["controllers"]:
            if controller["type"] != "auth":
                continue

            template = "controllers/auth_controller.tpl"
            content = self.template_engine.render(
                template,
                {
                    "controller_name": controller["name"],
                    "project_name": ir["project"],
                },
            )
            path = controllers_dir / f"{controller['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _generate_services(self, ir: dict) -> None:
        services_dir = self.output_dir / "services"
        services_dir.mkdir(parents=True, exist_ok=True)

        for service in ir["services"]:
            template = self._service_template(service["name"])
            content = self.template_engine.render(
                template,
                {
                    "class_name": service["name"],
                    "secret_key": f"{ir['project']}_prototype_secret",
                },
            )
            path = services_dir / f"{service['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _generate_middlewares(self, ir: dict) -> None:
        middleware_dir = self.output_dir / "middleware"
        middleware_dir.mkdir(parents=True, exist_ok=True)

        for middleware in ir["middlewares"]:
            template = "middleware/auth_middleware.tpl"
            content = self.template_engine.render(
                template,
                {
                    "class_name": middleware["name"],
                    "token_service_class": "TokenService",
                },
            )
            path = middleware_dir / f"{middleware['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _service_template(self, service_name: str) -> str:
        templates = {
            "PasswordHasher": "services/password_hasher.tpl",
            "TokenService": "services/token_service.tpl",
        }
        return templates[service_name]

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

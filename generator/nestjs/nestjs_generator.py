from pathlib import Path
import shutil

from generator.nestjs.name_utils import camel_case, pascal_case, pluralize, segment_name, typescript_type
from generator.php.template_engine import TemplateEngine
from generator.project_files import ProjectFileWriter


class NestJSGenerator:
    """Generates a minimal NestJS application structure from language-neutral IR."""

    HTTP_DECORATORS = {
        "GET": "Get",
        "POST": "Post",
        "PUT": "Put",
        "PATCH": "Patch",
        "DELETE": "Delete",
    }

    def __init__(self, output_dir: str = "output", debug: bool = False) -> None:
        self.output_dir = Path(output_dir)
        self.src_dir = self.output_dir / "src"
        self.template_engine = TemplateEngine(template_dir="templates/nestjs")
        self.debug = debug
        self.generated_components: list[dict[str, str]] = []

    def generate(self, ir: dict) -> None:
        self.generated_components = []
        self._prepare_output_dirs()

        module_imports = []
        module_names = []

        for model in ir["models"]:
            module_name = self._write_model_module(model, ir["routes"])
            module_imports.append(
                f"import {{ {module_name} }} from './modules/{self._folder_name(model['name'])}/{self._folder_name(model['name'])}.module';"
            )
            module_names.append(module_name)

        if ir.get("middlewares") or any(route["path"] == "/login" for route in ir["routes"]):
            self._write_auth_scaffold()
            module_imports.append("import { AuthModule } from './modules/auth/auth.module';")
            module_names.append("AuthModule")

        self._write(
            self.src_dir / "app.module.ts",
            "app.module.tpl",
            {
                "module_imports": "\n".join(module_imports),
                "modules": self._module_array(module_names),
            },
        )
        self._generate_project_template(ir)

        if self.debug:
            print("\n[NestJS Generator]")
            for component in self.generated_components:
                print(f"Created: {component['created']}")
                print(f"Template: {component['template']}")

    def _prepare_output_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for legacy_file in ["routes.php", "main.py"]:
            path = self.output_dir / legacy_file
            if path.exists():
                path.unlink()

        if self.src_dir.exists():
            shutil.rmtree(self.src_dir)
        self.src_dir.mkdir(parents=True, exist_ok=True)

        for cache_dir in self.output_dir.rglob("__pycache__"):
            shutil.rmtree(cache_dir)

        for directory in [
            "controllers",
            "models",
            "middleware",
            "config",
            "services",
            "repositories",
            "validators",
            "migrations",
            "routers",
            "schemas",
        ]:
            target = self.output_dir / directory
            if target.exists():
                shutil.rmtree(target)

    def _generate_project_template(self, ir: dict) -> None:
        writer = ProjectFileWriter(self.output_dir, self._record_project_file)
        (self.output_dir / "test").mkdir(parents=True, exist_ok=True)
        writer.write_text(
            "package.json",
            "\n".join(
                [
                    "{",
                    f"  \"name\": \"{self._package_name(ir['project'])}\",",
                    "  \"version\": \"0.1.0\",",
                    "  \"private\": true,",
                    "  \"scripts\": {",
                    "    \"start\": \"nest start\",",
                    "    \"start:dev\": \"nest start --watch\",",
                    "    \"test\": \"jest\"",
                    "  },",
                    "  \"dependencies\": {",
                    "    \"@nestjs/common\": \"latest\",",
                    "    \"@nestjs/core\": \"latest\",",
                    "    \"reflect-metadata\": \"latest\",",
                    "    \"rxjs\": \"latest\"",
                    "  },",
                    "  \"devDependencies\": {",
                    "    \"@nestjs/cli\": \"latest\",",
                    "    \"typescript\": \"latest\"",
                    "  }",
                    "}",
                    "",
                ]
            ),
            "nestjs package json",
        )
        writer.write_text(
            "nest-cli.json",
            "{\n  \"collection\": \"@nestjs/schematics\",\n  \"sourceRoot\": \"src\"\n}\n",
            "nestjs cli config",
        )
        writer.write_text(
            "tsconfig.json",
            "\n".join(
                [
                    "{",
                    "  \"compilerOptions\": {",
                    "    \"module\": \"commonjs\",",
                    "    \"target\": \"ES2021\",",
                    "    \"emitDecoratorMetadata\": true,",
                    "    \"experimentalDecorators\": true,",
                    "    \"strict\": true,",
                    "    \"outDir\": \"./dist\"",
                    "  }",
                    "}",
                    "",
                ]
            ),
            "nestjs tsconfig",
        )
        writer.write_text(
            "test/app.e2e-spec.ts",
            "describe('Generated app', () => {\n    it('exists', () => {\n        expect(true).toBe(true);\n    });\n});\n",
            "nestjs test placeholder",
        )
        writer.write_readme(ir, "nestjs")
        writer.write_env_example(
            ir,
            {
                "APP_NAME": ir["project"],
                "PORT": "3000",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "3306",
            },
        )
        writer.write_text(
            "Dockerfile",
            "\n".join(
                [
                    "FROM node:20-alpine",
                    "WORKDIR /app",
                    "COPY package.json .",
                    "RUN npm install",
                    "COPY . .",
                    "EXPOSE 3000",
                    "CMD [\"npm\", \"run\", \"start\"]",
                    "",
                ]
            ),
            "nestjs Dockerfile",
        )
        writer.write_text(
            "docker-compose.yml",
            "\n".join(
                [
                    "services:",
                    "  app:",
                    "    build: .",
                    "    ports:",
                    "      - \"3000:3000\"",
                    "",
                ]
            ),
            "nestjs docker compose",
        )
        writer.write_manifest(ir, "nestjs")

    def _record_project_file(self, path: Path, template: str) -> None:
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

    def _write_model_module(self, model: dict, routes: list[dict]) -> str:
        model_name = pascal_case(model["name"])
        folder = self._folder_name(model_name)
        module_dir = self.src_dir / "modules" / folder
        service_class = f"{model_name}Service"
        controller_class = f"{model_name}Controller"
        module_class = f"{model_name}Module"
        model_class = model_name

        self._write(
            module_dir / f"{self._file_stem(model_name)}.model.ts",
            "model.tpl",
            {
                "model_name": model_class,
                "fields": self._model_fields(model),
            },
        )
        self._write(
            module_dir / f"{folder}.service.ts",
            "service.tpl",
            {
                "service_name": service_class,
                "model_name": model_class,
                "model_file": self._file_stem(model_name),
                "property_name": camel_case(model_name),
            },
        )
        self._write(
            module_dir / f"{folder}.controller.ts",
            "controller.tpl",
            {
                "decorator_imports": self._controller_imports(model_name, routes),
                "controller_name": controller_class,
                "service_name": service_class,
                "service_file": folder,
                "service_property": camel_case(service_class),
                "route_prefix": folder,
                "methods": self._controller_methods(model_name, routes),
            },
        )
        self._write(
            module_dir / f"{folder}.module.ts",
            "module.tpl",
            {
                "module_name": module_class,
                "controller_name": controller_class,
                "service_name": service_class,
                "module_file": folder,
            },
        )
        return module_class

    def _write_auth_scaffold(self) -> None:
        guards_dir = self.src_dir / "guards"
        auth_dir = self.src_dir / "modules" / "auth"
        self._write(guards_dir / "auth.guard.ts", "auth.guard.tpl", {})
        self._write(auth_dir / "auth.service.ts", "auth.service.tpl", {})
        self._write(auth_dir / "auth.controller.ts", "auth.controller.tpl", {})
        self._write(auth_dir / "auth.module.ts", "auth.module.tpl", {})

    def _model_fields(self, model: dict) -> str:
        if not model["fields"]:
            return "    id!: number;"
        return "\n".join(
            f"    {field['name']}!: {typescript_type(field['type'])};"
            for field in model["fields"]
        )

    def _controller_imports(self, model_name: str, routes: list[dict]) -> str:
        decorators = {"Controller"}
        for route in self._routes_for_model(model_name, routes):
            decorators.add(self.HTTP_DECORATORS.get(route["method"], "Get"))
        return ", ".join(sorted(decorators))

    def _controller_methods(self, model_name: str, routes: list[dict]) -> str:
        blocks = []
        for route in self._routes_for_model(model_name, routes):
            decorator = self.HTTP_DECORATORS.get(route["method"], "Get")
            subpath = self._subpath_for_route(model_name, route["path"])
            method_name = self._method_name(route["method"], model_name, subpath)
            decorator_call = f"@{decorator}()" if not subpath else f"@{decorator}('{subpath}')"
            blocks.append(
                "\n".join(
                    [
                        f"    {decorator_call}",
                        f"    {method_name}() {{",
                        f"        return this.{camel_case(model_name)}Service.findAll();",
                        "    }",
                    ]
                )
            )
        if not blocks:
            blocks.append(
                "\n".join(
                    [
                        "    findAll() {",
                        f"        return this.{camel_case(model_name)}Service.findAll();",
                        "    }",
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _routes_for_model(self, model_name: str, routes: list[dict]) -> list[dict]:
        folder = self._folder_name(model_name)
        singular = segment_name(model_name)
        return [
            route
            for route in routes
            if self._first_segment(route["path"]) in {folder, singular}
        ]

    def _subpath_for_route(self, model_name: str, path: str) -> str:
        segments = [segment for segment in path.strip("/").split("/") if segment]
        if not segments:
            return ""
        if segments[0] in {self._folder_name(model_name), segment_name(model_name)}:
            return "/".join(segments[1:])
        return "/".join(segments)

    def _method_name(self, method: str, model_name: str, subpath: str) -> str:
        if method == "GET" and not subpath:
            return "findAll"
        if method == "GET":
            return "findOne"
        if method == "POST":
            return f"create{pascal_case(model_name)}"
        if method == "PUT":
            return f"update{pascal_case(model_name)}"
        if method == "PATCH":
            return f"patch{pascal_case(model_name)}"
        if method == "DELETE":
            return f"delete{pascal_case(model_name)}"
        return f"handle{pascal_case(method.lower())}{pascal_case(model_name)}"

    def _module_array(self, module_names: list[str]) -> str:
        if not module_names:
            return "[]"
        entries = "\n".join(f"        {module_name}," for module_name in module_names)
        return "[\n" + entries + "\n    ]"

    def _folder_name(self, model_name: str) -> str:
        return pluralize(segment_name(model_name))

    def _file_stem(self, model_name: str) -> str:
        return segment_name(model_name)

    def _first_segment(self, path: str) -> str:
        parts = [part for part in path.strip("/").split("/") if part]
        return parts[0].lower() if parts else ""

    def _package_name(self, project_name: str) -> str:
        return segment_name(project_name).replace("_", "-")

    def _write(self, path: Path, template: str, values: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.template_engine.render(template, values), encoding="utf-8")
        self.generated_components.append(
            {
                "created": str(path.relative_to(self.output_dir)),
                "template": template,
            }
        )

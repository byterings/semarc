from pathlib import Path

from generator.php.template_engine import TemplateEngine
from generator.utils.inflector import camel_case, pluralize


class RepositoryGenerator:
    def __init__(self, output_dir: Path, template_engine: TemplateEngine, reporter=None) -> None:
        self.output_dir = output_dir
        self.template_engine = template_engine
        self.reporter = reporter

    def generate(self, ir: dict) -> None:
        repositories_dir = self.output_dir / "repositories"
        repositories_dir.mkdir(parents=True, exist_ok=True)

        for repository in ir["repositories"]:
            template = self._template_for(repository)
            content = self.template_engine.render(
                template,
                {
                    "class_name": repository["name"],
                    "model_name": repository["model"],
                    "collection_name": self._collection_name(repository["model"]),
                    "create_method": f"create{repository['model']}",
                    "find_method": f"find{repository['model']}ById",
                    "list_method": f"get{self._pluralize(repository['model'])}",
                    "relationship_methods": self._relationship_methods(repository),
                },
            )
            path = repositories_dir / f"{repository['name']}.php"
            path.write_text(content, encoding="utf-8")
            self._report(path, template)

    def _template_for(self, repository: dict) -> str:
        return "repositories/user_repository.tpl"

    def _collection_name(self, model_name: str) -> str:
        return camel_case(pluralize(model_name))

    def _pluralize(self, model_name: str) -> str:
        return pluralize(model_name)

    def _relationship_methods(self, repository: dict) -> str:
        methods = []
        for dependency in repository.get("dependencies", []):
            related = dependency.removesuffix("Repository")
            method = related[0].lower() + related[1:] + "Records"
            methods.append(
                "\n".join(
                    [
                        "",
                        f"    public function {method}(int $parentId): array",
                        "    {",
                        "        return [];",
                        "    }",
                    ]
                )
            )
        return "\n".join(methods)

    def _report(self, path: Path, template: str) -> None:
        if self.reporter:
            self.reporter(path, template)

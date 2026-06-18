from generator.fastapi.mappers.name_utils import snake_case
from generator.utils.inflector import pluralize


class RepositoryMapper:
    """Maps IR repositories into FastAPI repository modules."""

    def map(self, ir: dict) -> list[dict]:
        mapped = []

        for repository in ir["repositories"]:
            model_name = repository["model"]
            collection_name = pluralize(snake_case(model_name))
            mapped.append(
                {
                    "path": f"repositories/{snake_case(repository['name'])}.py",
                    "template": "repository.tpl",
                    "values": {
                        "class_name": repository["name"],
                        "collection_name": collection_name,
                        "create_method": f"create_{snake_case(model_name)}",
                        "list_method": f"get_{collection_name}",
                        "relationship_methods": self._relationship_methods(repository),
                    },
                }
            )

        return mapped

    def _relationship_methods(self, repository: dict) -> str:
        methods = []
        for dependency in repository.get("dependencies", []):
            related = dependency.removesuffix("Repository")
            method_name = f"get_{snake_case(related)}_records"
            methods.append(
                "\n".join(
                    [
                        "",
                        f"    def {method_name}(self, parent_id: int) -> list:",
                        "        return []",
                    ]
                )
            )
        return "\n".join(methods)

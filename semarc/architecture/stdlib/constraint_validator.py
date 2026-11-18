from semarc.architecture.stdlib.module_definition import ModuleDefinition


class ModuleConstraintError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code} {message}")
        self.code = code


class ModuleConstraintValidator:
    """Validates resolved stdlib modules against architecture requirements and conflicts."""

    DATABASE_REQUIREMENTS = {
        "database.mysql": "MYSQL",
        "database.postgresql": "POSTGRESQL",
        "database.sqlite": "SQLITE",
    }
    TARGET_REQUIREMENTS = {
        "target.php": "PHP",
        "target.fastapi": "FASTAPI",
    }

    def validate(self, architecture, resolved_modules: list[ModuleDefinition]) -> None:
        loaded_module_names = {module.name.lower() for module in resolved_modules}
        database_engine = architecture.database.engine if architecture.database else "NONE"
        target_name = architecture.target.name if architecture.target else "PHP"

        for module in resolved_modules:
            for requirement in module.requirements:
                if not self._requirement_satisfied(
                    requirement,
                    loaded_module_names,
                    database_engine,
                    target_name,
                ):
                    raise ModuleConstraintError(
                        "SEM7001",
                        f"Module requirement not satisfied: {module.name} requires {requirement}",
                    )

            for conflict in module.conflicts:
                if conflict.lower() in loaded_module_names:
                    raise ModuleConstraintError(
                        "SEM7002",
                        f"Module conflict detected: {module.name} conflicts with {conflict}",
                    )

    def _requirement_satisfied(
        self,
        requirement: str,
        loaded_module_names: set[str],
        database_engine: str,
        target_name: str,
    ) -> bool:
        key = requirement.lower()
        if key in self.DATABASE_REQUIREMENTS:
            return database_engine == self.DATABASE_REQUIREMENTS[key]
        if key in self.TARGET_REQUIREMENTS:
            return target_name == self.TARGET_REQUIREMENTS[key]
        return key in loaded_module_names

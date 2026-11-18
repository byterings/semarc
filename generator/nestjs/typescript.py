"""Small helpers for emitting TypeScript source from Architecture IR."""
from generator.utils.inflector import camel_case, kebab_case, resource_path

TS_TYPES = {
    "STRING": "string",
    "TEXT": "string",
    "INTEGER": "number",
    "FLOAT": "number",
    "BOOLEAN": "boolean",
    "DATE": "string",
    "DATETIME": "Date",
}


def ts_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def folder(model_name: str) -> str:
    """Module folder, e.g. BlogPost -> blog-posts."""
    return resource_path(model_name)


def file_base(model_name: str) -> str:
    """Singular file prefix, e.g. BlogPost -> blog-post."""
    return kebab_case(model_name)


def service_property(model_name: str) -> str:
    return camel_case(model_name) + "Service"


def route_path(path: str) -> str:
    """Converts /posts/{id} to posts/:id for Nest route decorators."""
    segments = []
    for segment in path.strip("/").split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            segments.append(":" + segment[1:-1])
        elif segment:
            segments.append(segment)
    return "/".join(segments)


class Imports:
    """Collects named imports and aliases framework symbols that collide with model names."""

    def __init__(self, reserved: set[str]) -> None:
        self.reserved = reserved
        self.modules: dict[str, dict[str, str]] = {}

    def use(self, module: str, name: str) -> str:
        alias = f"{name}Decorator" if name in self.reserved and module.startswith(("@nestjs", "typeorm", "class-validator")) else name
        self.modules.setdefault(module, {})[name] = alias
        return alias

    def render(self) -> list[str]:
        lines = []
        external = sorted(module for module in self.modules if not module.startswith("."))
        local = sorted(module for module in self.modules if module.startswith("."))
        for module in external + local:
            names = sorted(self.modules[module].items())
            rendered = ", ".join(name if name == alias else f"{name} as {alias}" for name, alias in names)
            lines.append(f"import {{ {rendered} }} from {ts_string(module)};")
        return lines

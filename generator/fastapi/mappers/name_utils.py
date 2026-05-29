import re


def snake_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.lower()


def python_type(semantic_type: str) -> str:
    return {
        "STRING": "str",
        "TEXT": "str",
        "INTEGER": "int",
        "BOOLEAN": "bool",
        "FLOAT": "float",
    }.get(semantic_type, "str")

from generator.utils.inflector import snake_case


def python_type(semantic_type: str) -> str:
    return {
        "STRING": "str",
        "TEXT": "str",
        "INTEGER": "int",
        "BOOLEAN": "bool",
        "FLOAT": "float",
    }.get(semantic_type, "str")

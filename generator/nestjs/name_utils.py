from generator.utils.inflector import camel_case, pascal_case, pluralize


def segment_name(value: str) -> str:
    output = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            output.append("-")
        output.append(char.lower())
    return "".join(output)


def typescript_type(semantic_type: str) -> str:
    return {
        "STRING": "string",
        "TEXT": "string",
        "INTEGER": "number",
        "FLOAT": "number",
        "BOOLEAN": "boolean",
    }.get(semantic_type, "string")

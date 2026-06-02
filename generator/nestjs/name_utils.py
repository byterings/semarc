import re


def pascal_case(value: str) -> str:
    parts = re.split(r"[_\-\s]+", value)
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def camel_case(value: str) -> str:
    pascal = pascal_case(value)
    return pascal[:1].lower() + pascal[1:]


def segment_name(value: str) -> str:
    output = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            output.append("-")
        output.append(char.lower())
    return "".join(output)


def pluralize(value: str) -> str:
    if value.endswith("y") and len(value) > 1 and value[-2] not in "aeiou":
        return value[:-1] + "ies"
    if value.endswith("s"):
        return value
    return value + "s"


def typescript_type(semantic_type: str) -> str:
    return {
        "STRING": "string",
        "TEXT": "string",
        "INTEGER": "number",
        "FLOAT": "number",
        "BOOLEAN": "boolean",
    }.get(semantic_type, "string")

import re


IRREGULAR_PLURALS = {
    "person": "people",
    "Person": "People",
}


def pascal_case(value: str) -> str:
    parts = re.split(r"[_\-\s]+", value)
    return "".join(part[:1].upper() + part[1:] for part in parts if part)


def camel_case(value: str) -> str:
    pascal = pascal_case(value)
    return pascal[:1].lower() + pascal[1:]


def snake_case(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return value.replace("-", "_").lower()


def pluralize(value: str) -> str:
    if value in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[value]
    lower_value = value.lower()
    if lower_value in IRREGULAR_PLURALS:
        plural = IRREGULAR_PLURALS[lower_value]
        return plural[:1].upper() + plural[1:] if value[:1].isupper() else plural
    if value.endswith("y") and len(value) > 1 and value[-2].lower() not in "aeiou":
        return value[:-1] + "ies"
    if value.endswith(("s", "x", "z")) or value.endswith(("ch", "sh")):
        return value + "es"
    return value + "s"


def resource_path(model_name: str) -> str:
    return pluralize(snake_case(model_name)).replace("_", "-")

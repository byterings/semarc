"""Target-neutral views over Architecture IR models shared by every generator.

The IR describes models and routes. These helpers derive the concrete input
and output shapes that generated APIs expose, so every target applies the same
rules (for example the implicit 255 character limit of STRING columns).
"""

STRING_MAX_LENGTH = 255
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def field_rules(model_field: dict) -> dict:
    rules = model_field.get("rules", {})
    maximum = rules.get("max")
    if model_field["type"] == "STRING":
        maximum = STRING_MAX_LENGTH if maximum is None else min(maximum, STRING_MAX_LENGTH)
    return {
        "type": model_field["type"],
        "required": model_field["required"],
        "unique": model_field["unique"],
        "secret": model_field.get("secret", False),
        "not_empty": rules.get("not_empty", False),
        "email": rules.get("email", False),
        "min": rules.get("min"),
        "max": maximum,
    }


def reference_rules(reference: dict) -> dict:
    return {
        "type": "INTEGER",
        "required": True,
        "unique": reference["unique"],
        "secret": False,
        "not_empty": False,
        "email": False,
        "min": 1,
        "max": None,
    }


def input_fields(model: dict, include_owner: bool = True) -> dict[str, dict]:
    fields = {model_field["name"]: field_rules(model_field) for model_field in model["fields"]}
    for reference in model["references"]:
        if reference["owner"] and not include_owner:
            continue
        fields[reference["column"]] = reference_rules(reference)
    return fields


def output_fields(model: dict) -> list[tuple[str, str]]:
    fields = [("id", "INTEGER")]
    fields.extend(
        (model_field["name"], model_field["type"])
        for model_field in model["fields"]
        if not model_field.get("secret", False)
    )
    fields.extend((reference["column"], "INTEGER") for reference in model["references"])
    fields.extend([("created_at", "DATETIME"), ("updated_at", "DATETIME")])
    return fields


def secret_fields(model: dict) -> list[str]:
    return [model_field["name"] for model_field in model["fields"] if model_field.get("secret", False)]


def unique_columns(model: dict) -> list[str]:
    columns = [model_field["name"] for model_field in model["fields"] if model_field["unique"]]
    columns.extend(reference["column"] for reference in model["references"] if reference["unique"])
    return columns


def owner_reference(model: dict) -> dict | None:
    return next((reference for reference in model["references"] if reference["owner"]), None)


def model_by_name(ir: dict, name: str) -> dict:
    return next(model for model in ir["models"] if model["name"] == name)


def routes_for_model(ir: dict, model_name: str) -> list[dict]:
    return [
        route
        for route in ir["routes"]
        if route["operation"].get("model") == model_name and not route["operation"]["kind"].startswith("auth_")
    ]


def operation_kinds(ir: dict, model_name: str) -> list[str]:
    kinds = []
    for route in routes_for_model(ir, model_name):
        kind = route["operation"]["kind"]
        if kind not in kinds:
            kinds.append(kind)
    return kinds


def related_parents(ir: dict, model_name: str) -> list[dict]:
    parents = {}
    for route in routes_for_model(ir, model_name):
        operation = route["operation"]
        if operation["kind"] == "list_related":
            parents[operation["parent_model"]] = {
                "model": operation["parent_model"],
                "column": operation["foreign_key"],
                "table": model_by_name(ir, operation["parent_model"])["table"],
            }
    return [parents[name] for name in sorted(parents)]


def models_in_migration_order(ir: dict) -> list[dict]:
    order = [table["model"] for table in ir["migrations"].get("tables", [])]
    return [model_by_name(ir, name) for name in order]


def database_engine(ir: dict) -> str:
    engine = ir.get("config", {}).get("database", {}).get("engine", "NONE")
    return engine if engine in {"MYSQL", "POSTGRESQL", "SQLITE"} else "SQLITE"


def route_label(route: dict) -> str:
    return f"{route['method']} {route['path']}"


def all_route_labels(ir: dict) -> list[str]:
    return ["GET /", "GET /health", "GET /routes"] + [route_label(route) for route in ir["routes"]]

"""Renders SQLAlchemy models, Pydantic schemas, repositories and services from IR."""
from generator.utils.inflector import snake_case
from generator.utils.resource_views import field_rules, owner_reference, secret_fields, unique_columns

PYTHON_TYPES = {"STRING": "str", "TEXT": "str", "INTEGER": "int", "FLOAT": "float", "BOOLEAN": "bool"}
COLUMN_TYPES = {"STRING": "String(255)", "TEXT": "Text", "INTEGER": "Integer", "FLOAT": "Float", "BOOLEAN": "Boolean"}


def module_name(model_name: str) -> str:
    return snake_case(model_name)


def model_code(model: dict) -> str:
    sql_types = sorted({COLUMN_TYPES[model_field["type"]].split("(")[0] for model_field in model["fields"]} | {"DateTime", "Integer"})
    if model["references"]:
        sql_types = sorted(set(sql_types) | {"ForeignKey"})
    lines = [
        "from datetime import datetime",
        "",
        f"from sqlalchemy import {', '.join(sql_types)}",
        "from sqlalchemy.orm import Mapped, mapped_column",
        "",
        "from database import Base, utc_now",
        "",
    ]
    lines.extend(f"# Relation metadata: {relation['source']} {relation['type']} {relation['target']}" for relation in model["relations"])
    lines.extend(
        [
            "",
            "",
            f"class {model['name']}(Base):",
            f'    __tablename__ = "{model["table"]}"',
            "",
            "    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)",
        ]
    )
    for model_field in model["fields"]:
        annotation = PYTHON_TYPES[model_field["type"]]
        if not model_field["required"]:
            annotation += " | None"
        options = [COLUMN_TYPES[model_field["type"]], f"nullable={not model_field['required']}"]
        if model_field["unique"]:
            options.append("unique=True")
        lines.append(f"    {model_field['name']}: Mapped[{annotation}] = mapped_column({', '.join(options)})")
    for reference in model["references"]:
        options = ["Integer", f'ForeignKey("{reference["table"]}.id")', "nullable=False"]
        options.append("unique=True" if reference["unique"] else "index=True")
        lines.append(f"    {reference['column']}: Mapped[int] = mapped_column({', '.join(options)})")
    lines.extend(
        [
            "    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)",
            "    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)",
            "",
        ]
    )
    return "\n".join(lines)


def schema_code(model: dict) -> str:
    name = model["name"]
    rules = {model_field["name"]: field_rules(model_field) for model_field in model["fields"]}
    not_empty = [field for field, rule in rules.items() if rule["not_empty"]]
    emails = [field for field, rule in rules.items() if rule["email"]]
    required = [field for field, rule in rules.items() if rule["required"]]
    required += [reference["column"] for reference in model["references"] if not reference["owner"]]

    lines = [
        "from datetime import datetime",
        "",
        "from pydantic import Field, field_validator",
        "",
        "from schemas.base import InputSchema, OutputSchema, not_empty, not_null, valid_email",
        "",
        "",
        f"class {name}Create(InputSchema):",
    ]
    lines.extend(_input_fields(model, rules, optional=False))
    lines.extend(_validators(not_empty, emails, []))
    lines.extend(["", "", f"class {name}Update(InputSchema):"])
    lines.extend(_input_fields(model, rules, optional=True))
    lines.extend(_validators(not_empty, emails, required))
    lines.extend(["", "", f"class {name}Read(OutputSchema):", "    id: int"])
    for model_field in model["fields"]:
        if model_field.get("secret", False):
            continue
        annotation = PYTHON_TYPES[model_field["type"]] + ("" if model_field["required"] else " | None")
        lines.append(f"    {model_field['name']}: {annotation}")
    lines.extend(f"    {reference['column']}: int" for reference in model["references"])
    lines.extend(["    created_at: datetime", "    updated_at: datetime", ""])
    return "\n".join(lines)


def _input_fields(model: dict, rules: dict, optional: bool) -> list[str]:
    lines = []
    for field_name, rule in rules.items():
        annotation = PYTHON_TYPES[rule["type"]]
        options = []
        if optional or not rule["required"]:
            annotation += " | None"
            options.append("default=None")
        if rule["type"] in {"STRING", "TEXT"}:
            if rule["min"] is not None:
                options.append(f"min_length={rule['min']}")
            if rule["max"] is not None:
                options.append(f"max_length={rule['max']}")
        elif rule["type"] in {"INTEGER", "FLOAT"}:
            if rule["min"] is not None:
                options.append(f"ge={rule['min']}")
            if rule["max"] is not None:
                options.append(f"le={rule['max']}")
        default = f" = Field({', '.join(options)})" if options else ""
        lines.append(f"    {field_name}: {annotation}{default}")

    owner = owner_reference(model)
    for reference in model["references"]:
        if optional or reference is owner:
            comment = "  # taken from the bearer token on protected routes" if reference is owner else ""
            lines.append(f"    {reference['column']}: int | None = Field(default=None, ge=1){comment}")
        else:
            lines.append(f"    {reference['column']}: int = Field(ge=1)")
    return lines or ["    pass"]


def _validators(not_empty: list[str], emails: list[str], required: list[str]) -> list[str]:
    lines = []
    for attribute, fields, function in [
        ("_not_empty", not_empty, "not_empty"),
        ("_valid_email", emails, "valid_email"),
        ("_not_null", required, "not_null"),
    ]:
        if fields:
            arguments = ", ".join(f'"{field}"' for field in fields)
            lines.append(f"    {attribute} = field_validator({arguments})({function})")
    return ([""] + lines) if lines else []


def repository_code(model: dict) -> str:
    name = model["name"]
    return "\n".join(
        [
            f"from models.{module_name(name)} import {name}",
            "from repositories.base import Repository",
            "",
            "",
            f"class {name}Repository(Repository[{name}]):",
            f"    model = {name}",
            "",
        ]
    )


def service_code(model: dict, ir: dict) -> str:
    name = model["name"]
    module = module_name(name)
    secrets = secret_fields(model)
    imported_models = sorted({name} | {reference["model"] for reference in model["references"]} | {dependent["model"] for dependent in model["dependents"]})

    lines = ["from sqlalchemy.orm import Session", ""]
    lines.extend(f"from models.{module_name(other)} import {other}" for other in imported_models)
    lines.extend(
        [
            f"from repositories.{module}_repository import {name}Repository",
            f"from schemas.{module} import {name}Read",
            "from services.base import Dependent, Reference, ResourceService",
        ]
    )
    if secrets:
        lines.append("from services.password_hasher import PasswordHasher")
    lines.extend(["", "", f"class {name}Service(ResourceService[{name}]):", f'    name = "{name}"', f"    read_schema = {name}Read"])

    references = [
        f'Reference("{reference["column"]}", {reference["model"]}, "{reference["model"]}"'
        + (", owner=True)" if reference["owner"] else ")")
        for reference in model["references"]
    ]
    dependents = [
        f'Dependent({dependent["model"]}, "{dependent["column"]}", "{dependent["model"]}")'
        for dependent in model["dependents"]
    ]
    if references:
        lines.append(f"    references = ({', '.join(references)},)")
    if dependents:
        lines.append(f"    dependents = ({', '.join(dependents)},)")
    unique = unique_columns(model)
    if unique:
        lines.append(f"    unique = ({', '.join(repr(column) for column in unique)},)")

    lines.extend(
        [
            "",
            "    def __init__(self, session: Session) -> None:",
            f"        super().__init__({name}Repository(session))",
        ]
    )
    if secrets:
        lines.extend(
            [
                "        self.hasher = PasswordHasher()",
                "",
                "    def before_write(self, data: dict) -> dict:",
            ]
        )
        for secret in secrets:
            lines.extend(
                [
                    f'        if data.get("{secret}") is not None:',
                    f'            data["{secret}"] = self.hasher.hash(data["{secret}"])',
                ]
            )
        lines.append("        return data")
    lines.append("")
    return "\n".join(lines)

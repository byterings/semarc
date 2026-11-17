"""Renders Alembic revisions from the ordered IR migration plan."""
from generator.fastapi.entity_code import COLUMN_TYPES

ALEMBIC_TYPES = {
    "String(255)": "sa.String(length=255)",
    "Text": "sa.Text()",
    "Integer": "sa.Integer()",
    "Float": "sa.Float()",
    "Boolean": "sa.Boolean()",
}


def revision_id(sequence: int) -> str:
    return f"{sequence:04d}"


def migration_file_name(table: dict) -> str:
    return f"{revision_id(table['sequence'])}_create_{table['table']}_table.py"


def migration_code(table: dict, previous: dict | None) -> str:
    columns = ['        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),']
    for column in table["fields"]:
        options = [f'"{column["name"]}"', ALEMBIC_TYPES[COLUMN_TYPES[column["type"]]], f"nullable={not column['required']}"]
        if column["unique"]:
            options.append("unique=True")
        columns.append(f"        sa.Column({', '.join(options)}),")
    for foreign_key in table["foreign_keys"]:
        options = [
            f'"{foreign_key["column"]}"',
            "sa.Integer()",
            f'sa.ForeignKey("{foreign_key["references_table"]}.id")',
            "nullable=False",
        ]
        if foreign_key.get("unique"):
            options.append("unique=True")
        columns.append(f"        sa.Column({', '.join(options)}),")
    columns.extend(
        [
            '        sa.Column("created_at", sa.DateTime(), nullable=False),',
            '        sa.Column("updated_at", sa.DateTime(), nullable=False),',
        ]
    )
    indexes = [
        f'    op.create_index("ix_{table["table"]}_{foreign_key["column"]}", "{table["table"]}", ["{foreign_key["column"]}"])'
        for foreign_key in table["foreign_keys"]
        if not foreign_key.get("unique")
    ]
    down_revision = repr(revision_id(previous["sequence"])) if previous else "None"
    return "\n".join(
        [
            f'"""create {table["table"]} table',
            "",
            f"Revision ID: {revision_id(table['sequence'])}",
            f"Revises: {revision_id(previous['sequence']) if previous else ''}",
            '"""',
            "import sqlalchemy as sa",
            "from alembic import op",
            "",
            f'revision = "{revision_id(table["sequence"])}"',
            f"down_revision = {down_revision}",
            "branch_labels = None",
            "depends_on = None",
            "",
            "",
            "def upgrade() -> None:",
            "    op.create_table(",
            f'        "{table["table"]}",',
            *columns,
            "    )",
            *indexes,
            "",
            "",
            "def downgrade() -> None:",
            f'    op.drop_table("{table["table"]}")',
            "",
        ]
    )

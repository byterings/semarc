from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table

metadata = MetaData()

{{table_name}} = Table(
    "{{table_name}}",
    metadata,
    Column("id", Integer, primary_key=True),
{{columns}}
{{foreign_keys}}
)

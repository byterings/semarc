from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class {{model_name}}(Base):
    __tablename__ = "{{model_name}}".lower() + "s"
{{fields}}

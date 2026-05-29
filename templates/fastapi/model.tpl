from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class {{model_name}}(Base):
    __tablename__ = "{{model_name}}".lower() + "s"
{{fields}}

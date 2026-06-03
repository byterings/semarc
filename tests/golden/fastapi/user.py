from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "User".lower() + "s"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String)
    name = Column(String)

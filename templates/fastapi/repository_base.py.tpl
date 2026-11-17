from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import Base

ModelT = TypeVar("ModelT", bound=Base)


class Repository(Generic[ModelT]):
    """Generic SQLAlchemy persistence for one model. Subclasses set `model`."""

    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def paginate(self, limit: int, offset: int, filters: dict[str, Any] | None = None) -> list[ModelT]:
        statement = (
            select(self.model)
            .filter_by(**(filters or {}))
            .order_by(self.model.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count(self, filters: dict[str, Any] | None = None) -> int:
        statement = select(func.count()).select_from(self.model).filter_by(**(filters or {}))
        return int(self.session.scalar(statement) or 0)

    def get(self, record_id: int) -> ModelT | None:
        return self.session.get(self.model, record_id)

    def find_by(self, column: str, value: Any) -> ModelT | None:
        return self.session.scalars(select(self.model).filter_by(**{column: value}).limit(1)).first()

    def exists_where(self, column: str, value: Any, except_id: int | None = None) -> bool:
        statement = select(self.model.id).filter_by(**{column: value})
        if except_id is not None:
            statement = statement.where(self.model.id != except_id)
        return self.session.scalars(statement.limit(1)).first() is not None

    def row_exists(self, model: type[Base], record_id: int) -> bool:
        return self.session.get(model, record_id) is not None

    def count_in(self, model: type[Base], column: str, record_id: int) -> int:
        statement = select(func.count()).select_from(model).filter_by(**{column: record_id})
        return int(self.session.scalar(statement) or 0)

    def create(self, data: dict[str, Any]) -> ModelT:
        record = self.model(**data)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def update(self, record: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(record, key, value)
        self.session.commit()
        self.session.refresh(record)
        return record

    def delete(self, record: ModelT) -> None:
        self.session.delete(record)
        self.session.commit()

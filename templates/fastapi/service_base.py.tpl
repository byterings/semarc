import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from core.errors import ApiError
from database import Base
from repositories.base import Repository

ModelT = TypeVar("ModelT", bound=Base)

DEFAULT_LIMIT = {{default_limit}}
MAX_LIMIT = {{max_limit}}


@dataclass(frozen=True)
class Reference:
    column: str
    model: type[Base]
    name: str
    owner: bool = False


@dataclass(frozen=True)
class Dependent:
    model: type[Base]
    column: str
    name: str


class ResourceService(Generic[ModelT]):
    """Business rules shared by every generated resource: validation of
    references, uniqueness, ownership and safe deletes. Model services set the
    class attributes and can override before_write()."""

    name: str
    read_schema: type[BaseModel]
    references: tuple[Reference, ...] = ()
    dependents: tuple[Dependent, ...] = ()
    unique: tuple[str, ...] = ()
    filters: dict[str, str] = {"id": "INTEGER"}
    sort_fields: tuple[str, ...] = ("id",)

    def __init__(self, repository: Repository[ModelT]) -> None:
        self.repository = repository

    def list(
        self,
        limit: int,
        offset: int,
        query: Mapping[str, str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> dict:
        """Lists records; query holds equality filters and sort, where holds fixed conditions."""
        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        filters, order_by, descending = self._parse_query(query or {})
        filters.update(where or {})
        records = self.repository.paginate(limit, offset, filters, order_by, descending)
        return {
            "data": [self.serialize(record) for record in records],
            "meta": {"total": self.repository.count(filters), "limit": limit, "offset": offset},
        }

    def list_for_parent(
        self,
        parent: type[Base],
        parent_name: str,
        column: str,
        parent_id: int,
        limit: int,
        offset: int,
        query: Mapping[str, str] | None = None,
    ) -> dict:
        if not self.repository.row_exists(parent, parent_id):
            raise ApiError.not_found(f"{parent_name} {parent_id} not found.")
        return self.list(limit, offset, query, {column: parent_id})

    def get(self, record_id: int) -> dict:
        return self.serialize(self.find(record_id))

    def create(self, payload: BaseModel, owner_id: int | None = None) -> dict:
        data = payload.model_dump()
        self._apply_owner(data, owner_id, require=True)
        self._check_references(data)
        self._check_unique(data, None)
        return self.serialize(self.repository.create(self.before_write(data)))

    def update(self, record_id: int, payload: BaseModel, partial: bool, owner_id: int | None = None) -> dict:
        record = self.find(record_id)
        self._check_owner(record, owner_id)
        data = payload.model_dump(exclude_unset=partial)
        self._apply_owner(data, owner_id, require=not partial, keep_existing=True)
        if not data:
            return self.serialize(record)
        self._check_references(data)
        self._check_unique(data, record_id)
        return self.serialize(self.repository.update(record, self.before_write(data)))

    def delete(self, record_id: int, owner_id: int | None = None) -> None:
        record = self.find(record_id)
        self._check_owner(record, owner_id)
        for dependent in self.dependents:
            if self.repository.count_in(dependent.model, dependent.column, record_id) > 0:
                raise ApiError.conflict(
                    f"Cannot delete {self.name} {record_id} while {dependent.name} records reference it."
                )
        self.repository.delete(record)

    def before_write(self, data: dict[str, Any]) -> dict[str, Any]:
        """Hook for model specific changes before data is stored."""
        return data

    def serialize(self, record: ModelT) -> dict:
        return self.read_schema.model_validate(record).model_dump(mode="json")

    def find(self, record_id: int) -> ModelT:
        record = self.repository.get(record_id)
        if record is None:
            raise ApiError.not_found(f"{self.name} {record_id} not found.")
        return record

    def _parse_query(self, query: Mapping[str, str]) -> tuple[dict[str, Any], str, bool]:
        errors: dict[str, list[str]] = {}
        filters: dict[str, Any] = {}
        for field, field_type in self.filters.items():
            if field not in query:
                continue
            value = _filter_value(query[field], field_type)
            if value is None:
                errors[field] = [f"{field} filter must be {FILTER_DESCRIPTIONS.get(field_type, 'text')}"]
            else:
                filters[field] = value

        order_by, descending = "id", False
        if "sort" in query:
            sort = query["sort"]
            if sort.lstrip("-") not in self.sort_fields:
                choices = ", ".join(self.sort_fields)
                errors["sort"] = [f"sort must be one of: {choices} (prefix with - for descending)"]
            else:
                order_by, descending = sort.lstrip("-"), sort.startswith("-")

        if errors:
            raise ApiError.validation(errors)
        return filters, order_by, descending

    def _check_owner(self, record: ModelT, owner_id: int | None) -> None:
        """On protected routes, records with an owner column may only be changed by their owner."""
        if owner_id is None:
            return
        for reference in self.references:
            if reference.owner and getattr(record, reference.column) != owner_id:
                raise ApiError.forbidden(f"Only the owner can modify this {self.name}.")

    def _apply_owner(self, data: dict[str, Any], owner_id: int | None, require: bool, keep_existing: bool = False) -> None:
        for reference in self.references:
            if not reference.owner:
                continue
            if owner_id is not None:
                if keep_existing:
                    data.pop(reference.column, None)
                else:
                    data[reference.column] = owner_id
            elif require and data.get(reference.column) is None:
                raise ApiError.validation({reference.column: [f"{reference.column} is required"]})

    def _check_references(self, data: dict[str, Any]) -> None:
        errors: dict[str, list[str]] = {}
        for reference in self.references:
            value = data.get(reference.column)
            if value is not None and not self.repository.row_exists(reference.model, value):
                errors[reference.column] = [f"{reference.column} does not reference an existing {reference.name}"]
        if errors:
            raise ApiError.validation(errors)

    def _check_unique(self, data: dict[str, Any], except_id: int | None) -> None:
        errors: dict[str, list[str]] = {}
        for column in self.unique:
            value = data.get(column)
            if value is not None and self.repository.exists_where(column, value, except_id):
                errors[column] = [f"{column} has already been taken"]
        if errors:
            raise ApiError.conflict(f"{self.name} already exists.", errors)


FILTER_DESCRIPTIONS = {
    "INTEGER": "an integer",
    "FLOAT": "a number",
    "BOOLEAN": "true or false",
    "DATE": "a date (YYYY-MM-DD)",
}


def _filter_value(raw: str, field_type: str) -> Any:
    if field_type == "INTEGER":
        return int(raw) if re.fullmatch(r"-?\d+", raw) else None
    if field_type == "FLOAT":
        try:
            return float(raw)
        except ValueError:
            return None
    if field_type == "BOOLEAN":
        return {"true": True, "1": True, "false": False, "0": False}.get(raw.lower())
    if field_type == "DATE":
        try:
            return date.fromisoformat(raw) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw) else None
        except ValueError:
            return None
    return raw

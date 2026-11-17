import re
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

T = TypeVar("T")


class InputSchema(BaseModel):
    """Request bodies: strict JSON types, unknown fields ignored."""

    model_config = ConfigDict(strict=True, extra="ignore")


class OutputSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_timestamp(self, value: datetime) -> str:
        return value.replace(microsecond=0).isoformat() + "Z"


class Meta(BaseModel):
    total: int
    limit: int
    offset: int


class DataResponse(BaseModel, Generic[T]):
    data: T


class ListResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: Meta


def not_empty(value: str | None) -> str | None:
    if value is not None and value.strip() == "":
        raise ValueError("must not be empty")
    return value


def valid_email(value: str | None) -> str | None:
    if value is not None and not EMAIL_PATTERN.match(value):
        raise ValueError("must be a valid email address")
    return value


def not_null(value):
    if value is None:
        raise ValueError("is required")
    return value

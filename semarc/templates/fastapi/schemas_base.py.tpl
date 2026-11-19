import re
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

T = TypeVar("T")


class InputSchema(BaseModel):
    """Request bodies: strict JSON types, unknown fields ignored."""

    model_config = ConfigDict(strict=True, extra="ignore")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(lambda value: value.replace(microsecond=0).isoformat() + "Z", return_type=str),
]
"""A naive UTC datetime rendered as ISO 8601 with a Z suffix."""


def _iso_text(value):
    if not isinstance(value, str):
        raise ValueError("must be an ISO 8601 string")
    return value


IsoDate = Annotated[date, BeforeValidator(_iso_text), Field(strict=False)]
"""Request date: a YYYY-MM-DD string."""

IsoDateTime = Annotated[datetime, BeforeValidator(_iso_text), Field(strict=False)]
"""Request date-time: an ISO 8601 string; offsets are converted to UTC."""

DECIMAL_PATTERN = re.compile(r"^-?\d{1,10}(\.\d{1,2})?$")


def _decimal_input(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("must be a decimal number")
    if isinstance(value, float):
        if value != value or round(value, 2) != value:
            raise ValueError("must have at most 2 decimals")
        value = f"{value:.2f}"
    text = str(value)
    if not DECIMAL_PATTERN.match(text):
        raise ValueError("must be a decimal with at most 10 digits before and 2 after the point")
    return Decimal(text)


DecimalInput = Annotated[Decimal, BeforeValidator(_decimal_input), Field(strict=False)]
"""Request decimal: a JSON number or numeric string with up to 2 decimals."""

DecimalText = Annotated[Decimal, PlainSerializer(lambda value: f"{value:.2f}", return_type=str)]
"""A DECIMAL rendered as a string with exactly 2 decimals."""


class OutputSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


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


def utc_naive(value: datetime | None) -> datetime | None:
    """Stores datetimes as naive UTC; values without an offset are already UTC."""
    if value is None:
        return value
    if value.tzinfo is not None:
        value = value.astimezone(UTC).replace(tzinfo=None)
    return value.replace(microsecond=0)

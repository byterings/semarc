"""Typed values written in the semantic source (DEFAULT and VALIDATE ... IN).

The source holds one token per value; this module turns it into the IR value for the
field type, or explains why it does not fit. DECIMAL values stay strings with exactly
DECIMAL_SCALE decimals so every target stores and returns the same text.
"""
import re
from datetime import date

DECIMAL_PRECISION = 12
DECIMAL_SCALE = 2
DECIMAL_PATTERN = re.compile(r"^-?\d{1,%d}(\.\d{1,%d})?$" % (DECIMAL_PRECISION - DECIMAL_SCALE, DECIMAL_SCALE))
INTEGER_PATTERN = re.compile(r"^-?\d{1,18}$")
FLOAT_PATTERN = re.compile(r"^-?\d+(\.\d+)?$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STRING_LIMIT = 255


def parse_value(field_type: str, text: str):
    """Returns (value, None) or (None, reason)."""
    if field_type == "INTEGER":
        return (int(text), None) if INTEGER_PATTERN.match(text) else (None, "an integer")
    if field_type == "FLOAT":
        return (float(text), None) if FLOAT_PATTERN.match(text) else (None, "a number")
    if field_type == "DECIMAL":
        if not DECIMAL_PATTERN.match(text):
            return None, f"a decimal with up to {DECIMAL_PRECISION - DECIMAL_SCALE} digits and {DECIMAL_SCALE} decimals"
        whole, _, fraction = text.partition(".")
        return f"{whole}.{fraction.ljust(DECIMAL_SCALE, '0')}", None
    if field_type == "BOOLEAN":
        return ({"true": True, "false": False}[text], None) if text in {"true", "false"} else (None, "true or false")
    if field_type == "DATE":
        if DATE_PATTERN.match(text):
            try:
                date.fromisoformat(text)
                return text, None
            except ValueError:
                pass
        return None, "a date (YYYY-MM-DD)"
    if field_type == "STRING":
        return (text, None) if len(text) <= STRING_LIMIT else (None, f"at most {STRING_LIMIT} characters")
    if field_type == "TEXT":
        return text, None
    return None, f"not supported for {field_type}"


def decimal_value(text: str) -> float:
    return float(text)

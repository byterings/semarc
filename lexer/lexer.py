from dataclasses import dataclass
from typing import List


KEYWORDS = {
    "PROJECT",
    "TARGET",
    "DATABASE",
    "AUTH",
    "CONFIG",
    "MODEL",
    "PROFILE",
    "ROUTE",
    "SERVICE",
    "RELATION",
    "USE",
    "VALIDATE",
}
TYPES = {"STRING", "INTEGER", "BOOLEAN", "FLOAT", "TEXT"}
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
RELATION_TYPES = {"HAS_MANY", "BELONGS_TO", "HAS_ONE"}
FIELD_MODIFIERS = {"UNIQUE", "OPTIONAL"}
ROUTE_ACCESS = {"PUBLIC", "PROTECTED"}
VALIDATION_RULES = {"REQUIRED", "EMAIL", "MIN", "MAX"}
RESERVED_KEYWORDS = {"CONFIG", "SERVICE"}


@dataclass(frozen=True)
class Token:
    token_type: str
    value: str
    line: int
    column: int
    indent: int = 0


class Lexer:
    """Converts a semantic source file into deterministic line-based tokens."""

    def tokenize(self, source: str) -> List[List[Token]]:
        token_lines: List[List[Token]] = []

        for line_number, raw_line in enumerate(source.splitlines(), start=1):
            if not raw_line.strip():
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" "))
            parts = raw_line.strip().split()
            tokens: List[Token] = []
            search_start = indent

            for part in parts:
                column = raw_line.find(part, search_start) + 1
                search_start = column + len(part) - 1
                tokens.append(
                    Token(
                        token_type=self._classify(part),
                        value=part,
                        line=line_number,
                        column=column,
                        indent=indent,
                    )
                )

            token_lines.append(tokens)

        return token_lines

    def _classify(self, value: str) -> str:
        upper_value = value.upper()

        if value in KEYWORDS:
            return "KEYWORD"
        if value == upper_value and upper_value in TYPES:
            return "TYPE"
        if value == upper_value and upper_value in HTTP_METHODS:
            return "HTTP_METHOD"
        if value == upper_value and upper_value in RELATION_TYPES:
            return "RELATION_TYPE"
        if value.startswith("/"):
            return "STRING"
        if value.isdigit():
            return "NUMBER"
        return "IDENTIFIER"

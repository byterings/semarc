from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ArchitectureRule:
    rule_id: str
    severity: str
    title: str
    message: str
    evaluator: Callable[[dict, object], None]

    def evaluate(self, context: dict, result) -> None:
        self.evaluator(context, result)

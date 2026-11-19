from dataclasses import dataclass, field


@dataclass
class ConstraintResult:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    score: int = 100
    rules_executed: int = 0

    def add_error(self, diagnostic) -> None:
        self.errors.append(diagnostic)

    def add_warning(self, diagnostic) -> None:
        self.warnings.append(diagnostic)

    def add_recommendation(self, diagnostic) -> None:
        self.recommendations.append(diagnostic)

    def finalize_score(self) -> None:
        penalty = (len(self.errors) * 30) + (len(self.warnings) * 5) + (len(self.recommendations) * 2)
        self.score = max(0, 100 - penalty)

    def merge(self, other: "ConstraintResult") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.recommendations.extend(other.recommendations)
        self.rules_executed += other.rules_executed

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "rules_executed": self.rules_executed,
            "errors": [diagnostic.to_dict() for diagnostic in self.errors],
            "warnings": [diagnostic.to_dict() for diagnostic in self.warnings],
            "recommendations": [diagnostic.to_dict() for diagnostic in self.recommendations],
        }

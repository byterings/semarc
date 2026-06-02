from dataclasses import dataclass, field


@dataclass
class ArchitectureAnalysisResult:
    warnings: list = field(default_factory=list)
    recommendations: list = field(default_factory=list)
    rules_executed: int = 0

    def add_warning(self, diagnostic) -> None:
        self.warnings.append(diagnostic)

    def add_recommendation(self, diagnostic) -> None:
        self.recommendations.append(diagnostic)

    def to_dict(self) -> dict:
        return {
            "rules_executed": self.rules_executed,
            "warnings": [diagnostic.to_dict() for diagnostic in self.warnings],
            "recommendations": [diagnostic.to_dict() for diagnostic in self.recommendations],
        }

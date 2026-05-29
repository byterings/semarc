from dataclasses import dataclass


@dataclass(frozen=True)
class Diagnostic:
    diagnostic_type: str
    code: str
    message: str
    severity: str
    source: str

    def to_dict(self) -> dict:
        return {
            "type": self.diagnostic_type,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
        }


class DiagnosticError(Diagnostic):
    def __init__(self, code: str, message: str, source: str) -> None:
        super().__init__("error", code, message, "error", source)


class DiagnosticWarning(Diagnostic):
    def __init__(self, code: str, message: str, source: str) -> None:
        super().__init__("warning", code, message, "warning", source)


class DiagnosticRecommendation(Diagnostic):
    def __init__(self, code: str, message: str, source: str) -> None:
        super().__init__("recommendation", code, message, "info", source)

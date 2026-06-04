class ContractError(Exception):
    """Raised when generation contract validation fails."""

    def __init__(self, message: str, code: str = "SEMGEN001") -> None:
        self.code = code
        super().__init__(f"[Generation Contract Error]\nCode: {code}\n{message}")

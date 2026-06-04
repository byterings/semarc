class TokenService:
    def generate(self, payload: dict) -> str:
        raise NotImplementedError("TODO: configure a real token provider.")

    def validate(self, token: str):
        raise NotImplementedError("TODO: configure a real token validator.")

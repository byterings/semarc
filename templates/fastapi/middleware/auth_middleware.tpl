from fastapi import HTTPException, Request

from services.token_service import TokenService


class AuthMiddleware:
    def __init__(self):
        self.tokens = TokenService()

    def handle(self, request: Request):
        header = request.headers.get("authorization", "")
        token = self._extract_bearer_token(header)

        if token is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        payload = self.tokens.validate(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return payload

    def _extract_bearer_token(self, header: str):
        if not header.startswith("Bearer "):
            return None
        return header[7:].strip()

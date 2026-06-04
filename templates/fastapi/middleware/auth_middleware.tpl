from fastapi import HTTPException, Request

from services.token_service import TokenService


class AuthMiddleware:
    def __init__(self):
        self.tokens = TokenService()

    def handle(self, request: Request):
        raise HTTPException(
            status_code=501,
            detail="Authentication middleware is a generated TODO scaffold.",
        )

    def _extract_bearer_token(self, header: str):
        if not header.startswith("Bearer "):
            return None
        return header[7:].strip()

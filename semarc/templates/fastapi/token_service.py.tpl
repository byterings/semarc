import time

import jwt

from config.settings import settings
from core.errors import ApiError

MIN_SECRET_LENGTH = 32


class TokenService:
    """Issues and verifies HS256 JSON Web Tokens."""

    def issue(self, user_id: int) -> dict:
        now = int(time.time())
        claims = {"sub": str(user_id), "iat": now, "exp": now + settings.jwt_ttl}
        return {
            "access_token": jwt.encode(claims, self._secret(), algorithm="HS256"),
            "token_type": "Bearer",
            "expires_in": settings.jwt_ttl,
        }

    def user_id_from(self, token: str) -> int:
        try:
            claims = jwt.decode(token, self._secret(), algorithms=["HS256"], options={"require": ["exp", "sub"]})
        except jwt.ExpiredSignatureError as error:
            raise ApiError.unauthorized("Token has expired.") from error
        except jwt.PyJWTError as error:
            raise ApiError.unauthorized("Invalid token.") from error

        subject = claims["sub"]
        if not isinstance(subject, str) or not subject.isdigit() or int(subject) < 1:
            raise ApiError.unauthorized("Invalid token subject.")
        return int(subject)

    def _secret(self) -> str:
        if len(settings.jwt_secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(f"JWT_SECRET must be set to at least {MIN_SECRET_LENGTH} characters.")
        return settings.jwt_secret

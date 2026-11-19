"""Server-side sessions behind an HttpOnly cookie.

Only SHA-256 hashes of the session token and of its CSRF token are stored. POST, PUT, PATCH
and DELETE requests must send the CSRF token (also readable from the {{csrf_cookie}} cookie)
in the {{csrf_header}} header.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Response
from sqlalchemy import DateTime, ForeignKey, Integer, String, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from config.settings import settings
from database import Base, utc_now

COOKIE = "{{cookie}}"
CSRF_COOKIE = "{{csrf_cookie}}"
CSRF_HEADER = "{{csrf_header}}"


class UserSession(Base):
    __tablename__ = "{{table}}"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    csrf_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("{{users_table}}.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _set_cookie(response: Response, name: str, value: str, max_age: int, http_only: bool) -> None:
    response.set_cookie(
        name, value, max_age=max_age, path="/", samesite="lax", httponly=http_only, secure=settings.session_secure_cookie
    )


class SessionStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def issue(self, user_id: int, response: Response) -> dict:
        """Starts a session and sets the session and CSRF cookies."""
        token, csrf = secrets.token_hex(32), secrets.token_hex(32)
        self.session.add(
            UserSession(
                user_id=user_id,
                token_hash=hash_token(token),
                csrf_hash=hash_token(csrf),
                expires_at=utc_now() + timedelta(seconds=settings.session_ttl),
            )
        )
        self.session.commit()
        _set_cookie(response, COOKIE, token, settings.session_ttl, True)
        _set_cookie(response, CSRF_COOKIE, csrf, settings.session_ttl, False)
        return {"csrf_token": csrf, "expires_in": settings.session_ttl}

    def find(self, token: str | None) -> UserSession | None:
        """The active session for a cookie value, or None when missing, ended or expired."""
        if not token:
            return None
        record = self.session.scalars(select(UserSession).filter_by(token_hash=hash_token(token))).first()
        if record is None or record.revoked_at is not None or record.expires_at <= utc_now():
            return None
        return record

    def end(self, token: str | None, response: Response) -> None:
        """Ends a session and clears its cookies."""
        if token:
            self.session.execute(
                update(UserSession)
                .where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None))
                .values(revoked_at=utc_now())
            )
            self.session.commit()
        _set_cookie(response, COOKIE, "", 0, True)
        _set_cookie(response, CSRF_COOKIE, "", 0, False)

    def revoke_all(self, user_id: int) -> None:
        self.session.execute(
            update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)).values(revoked_at=utc_now())
        )
        self.session.commit()

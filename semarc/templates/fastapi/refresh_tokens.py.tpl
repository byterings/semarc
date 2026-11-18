import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from config.settings import settings
from core.errors import ApiError
from database import Base, utc_now


class RefreshToken(Base):
    """Opaque, rotating refresh tokens; only a SHA-256 hash of each token is stored."""

    __tablename__ = "{{table}}"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("{{users_table}}.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def issue(self, user_id: int) -> dict:
        token = secrets.token_hex(32)
        self.session.add(
            RefreshToken(
                user_id=user_id,
                token_hash=_hash(token),
                expires_at=utc_now() + timedelta(seconds=settings.jwt_refresh_ttl),
            )
        )
        self.session.commit()
        return {"refresh_token": token, "refresh_expires_in": settings.jwt_refresh_ttl}

    def rotate(self, token: str) -> int:
        """Revokes a valid token and returns its user id; invalid, expired or reused tokens get 401."""
        record = self.session.scalars(select(RefreshToken).filter_by(token_hash=_hash(token))).first()
        if record is None or record.revoked_at is not None or record.expires_at <= utc_now():
            raise ApiError.unauthorized("Invalid or expired refresh token.")
        record.revoked_at = utc_now()
        self.session.commit()
        return record.user_id

    def revoke(self, token: str) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == _hash(token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        self.session.commit()

    def revoke_all(self, user_id: int) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        self.session.commit()

import hmac

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from core.errors import ApiError
from core.sessions import COOKIE, CSRF_HEADER, SessionStore, hash_token
from database import get_db
from models.{{auth_module}} import {{auth_model}}

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def current_user_id(request: Request, db: Session = Depends(get_db)) -> int:
    """Resolves the user of the session cookie (401); unsafe methods also need the CSRF header (403)."""
    record = SessionStore(db).find(request.cookies.get(COOKIE))
    if record is None:
        raise ApiError.unauthorized("Missing, ended or expired session.")
    if request.method not in SAFE_METHODS:
        csrf = request.headers.get(CSRF_HEADER)
        if csrf is None or not hmac.compare_digest(record.csrf_hash, hash_token(csrf)):
            raise ApiError.forbidden("Missing or invalid CSRF token.")
    if db.get({{auth_model}}, record.user_id) is None:
        raise ApiError.unauthorized("Session user no longer exists.")
    return record.user_id
{{roles_code}}
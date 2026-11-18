from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.errors import ApiError
from database import get_db
from models.{{auth_module}} import {{auth_model}}
from services.token_service import TokenService

bearer_scheme = HTTPBearer(auto_error=False)


def current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> int:
    """Resolves the authenticated user id from the bearer token or responds 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError.unauthorized("Missing bearer token.")
    user_id = TokenService().user_id_from(credentials.credentials)
    if db.get({{auth_model}}, user_id) is None:
        raise ApiError.unauthorized("Token user no longer exists.")
    return user_id

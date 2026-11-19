"""Sign-in with OAuth providers (authorization code flow).

GET /oauth/<provider> returns the provider authorization URL and a signed `state`. The
front end sends the user there; the provider redirects back to OAUTH_<PROVIDER>_REDIRECT_URI
with `code` and `state`, which the front end posts to POST /oauth/<provider>/callback. The
front end must check that the returned `state` equals the one it received.
"""
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from config.settings import env, settings
from core.errors import ApiError
from database import Base, utc_now

STATE_TTL_SECONDS = {{state_ttl}}
TIMEOUT_SECONDS = 10
MIN_SECRET_LENGTH = 32
{{providers}}


class OAuthAccount(Base):
    """Links a provider identity (provider:subject) to a user."""

    __tablename__ = "{{table}}"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("{{users_table}}.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)


def _config(provider: str) -> dict:
    prefix = "OAUTH_" + provider.upper()
    config = {
        "client_id": env(prefix + "_CLIENT_ID"),
        "client_secret": env(prefix + "_CLIENT_SECRET"),
        "redirect_uri": env(prefix + "_REDIRECT_URI"),
        "endpoint": env(prefix + "_ENDPOINT"),
    }
    if not (config["client_id"] and config["client_secret"] and config["redirect_uri"]):
        raise ApiError(503, "service_unavailable", f"OAuth provider {provider} is not configured.")
    return config


def _url(config: dict, url: str) -> str:
    """OAUTH_<PROVIDER>_ENDPOINT replaces the provider origin (used with a mock provider in tests)."""
    if not config["endpoint"]:
        return url
    endpoint = urlsplit(config["endpoint"])
    return urlsplit(url)._replace(scheme=endpoint.scheme, netloc=endpoint.netloc).geturl()


def _signature(payload: str) -> str:
    if len(settings.jwt_secret) < MIN_SECRET_LENGTH:
        raise RuntimeError(f"JWT_SECRET must be set to at least {MIN_SECRET_LENGTH} characters.")
    return hmac.new(settings.jwt_secret.encode(), ("oauth-state:" + payload).encode(), hashlib.sha256).hexdigest()


def start(provider: str) -> dict:
    config = _config(provider)
    details = PROVIDERS[provider]
    payload = f"{provider}.{int(time.time()) + STATE_TTL_SECONDS}.{secrets.token_hex(16)}"
    state = payload + "." + _signature(payload)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": " ".join(details["scopes"]),
            "state": state,
        },
        quote_via=quote,
    )
    return {"authorization_url": _url(config, details["authorize_url"]) + "?" + query, "state": state}


def verify_state(provider: str, state: str) -> None:
    parts = state.split(".")
    valid = (
        len(parts) == 4
        and parts[0] == provider
        and parts[1].isdigit()
        and int(parts[1]) > time.time()
        and hmac.compare_digest(parts[3], _signature(".".join(parts[:3])))
    )
    if not valid:
        raise ApiError.validation({"state": ["state is invalid or expired"]})


def _request(provider: str, url: str, data: dict | None = None, token: str | None = None):
    headers = {"Accept": "application/json", "User-Agent": settings.app_name}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = urlencode(data).encode() if data is not None else None
    try:
        with urlopen(Request(url, data=body, headers=headers), timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except HTTPError as error:
        if data is not None and 400 <= error.code < 500:
            raise ApiError.validation({"code": ["code is invalid or expired"]}) from error
        raise ApiError(502, "bad_gateway", f"OAuth provider {provider} returned an error.") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise ApiError(502, "bad_gateway", f"OAuth provider {provider} is unavailable.") from error


def fetch_identity(provider: str, code: str) -> dict:
    """Exchanges the code and returns subject, verified email and display name."""
    config = _config(provider)
    details = PROVIDERS[provider]
    tokens = _request(
        provider,
        _url(config, details["token_url"]),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
        },
    )
    access_token = tokens.get("access_token") if isinstance(tokens, dict) else None
    if not isinstance(access_token, str) or not access_token:
        raise ApiError.validation({"code": ["code is invalid or expired"]})

    profile = _request(provider, _url(config, details["profile_url"]), token=access_token)
    if not isinstance(profile, dict) or profile.get(details["subject_field"]) in (None, ""):
        raise ApiError(502, "bad_gateway", f"OAuth provider {provider} returned an unexpected profile.")
    email = None
    if details["emails_url"]:
        addresses = _request(provider, _url(config, details["emails_url"]), token=access_token)
        for address in addresses if isinstance(addresses, list) else []:
            if isinstance(address, dict) and address.get("primary") is True and address.get("verified") is True:
                email = address.get("email")
    elif profile.get(details["verified_field"]) is True:
        email = profile.get(details["email_field"])
    if not isinstance(email, str) or "@" not in email:
        raise ApiError.validation({"email": [f"{provider} did not confirm a verified email address"]})

    name = profile.get(details["name_field"])
    if not isinstance(name, str) or not name.strip():
        name = email.split("@")[0]
    return {"subject": f"{provider}:{profile[details['subject_field']]}", "email": email, "name": name.strip()}

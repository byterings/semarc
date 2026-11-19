"""Deterministic OAuth provider for end-to-end tests of generated projects.

Serves the Google and GitHub endpoints SEMARC projects call, under their real paths, so a
project pointed at this server with OAUTH_<PROVIDER>_ENDPOINT behaves as with the real
provider. An authorization code has the form "email|verified|name" (verified is 1 or 0);
any other code is rejected like an expired one. The token endpoints require the client
credentials and redirect URI used by api_scenario.json.

Usage: python oauth_mock.py [port]   (default 9000; standard library only)
"""
import base64
import hashlib
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

CLIENT_ID = "semarc-test-client"
CLIENT_SECRET = "semarc-test-secret"
TOKEN_PATHS = {"/token": "google", "/login/oauth/access_token": "github"}


def parse_code(code: str) -> dict | None:
    parts = code.split("|")
    if len(parts) != 3 or "@" not in parts[0] or parts[1] not in {"0", "1"}:
        return None
    return {"email": parts[0], "verified": parts[1] == "1", "name": parts[2]}


def subject(email: str) -> int:
    return int(hashlib.sha256(email.encode()).hexdigest()[:12], 16)


class Handler(BaseHTTPRequestHandler):
    server_version = "SemarcOAuthMock/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - signature from the base class
        sys.stderr.write("oauth-mock: " + format % args + "\n")

    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        provider = TOKEN_PATHS.get(self.path)
        if provider is None:
            self._json(404, {"error": "not_found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = {key: values[0] for key, values in parse_qs(self.rfile.read(length).decode()).items()}
        expected_redirect = f"https://app.example.com/oauth/{provider}/callback"
        valid_client = (
            form.get("grant_type") == "authorization_code"
            and form.get("client_id") == CLIENT_ID
            and form.get("client_secret") == CLIENT_SECRET
            and form.get("redirect_uri") == expected_redirect
        )
        if not valid_client:
            self._json(401, {"error": "invalid_client"})
            return
        if parse_code(form.get("code", "")) is None:
            # GitHub reports errors with status 200; Google with 400.
            self._json(200 if provider == "github" else 400, {"error": "invalid_grant"})
            return
        token = base64.urlsafe_b64encode(form["code"].encode()).decode()
        self._json(200, {"access_token": token, "token_type": "bearer", "scope": "email"})

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        authorization = self.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            self._json(401, {"error": "missing token"})
            return
        try:
            profile = parse_code(base64.urlsafe_b64decode(authorization.removeprefix("Bearer ").encode()).decode())
        except ValueError:
            profile = None
        if profile is None:
            self._json(401, {"error": "invalid token"})
            return
        github = self.path.startswith("/user")
        if github and not self.headers.get("User-Agent"):
            self._json(403, {"message": "Request forbidden by administrative rules. Please make sure your request has a User-Agent header"})
            return
        if self.path == "/v1/userinfo":
            self._json(
                200,
                {"sub": str(subject(profile["email"])), "email": profile["email"], "email_verified": profile["verified"], "name": profile["name"]},
            )
        elif self.path == "/user":
            self._json(200, {"id": subject(profile["email"]), "login": profile["email"].split("@")[0], "name": profile["name"], "email": None})
        elif self.path == "/user/emails":
            self._json(
                200,
                [
                    {"email": "secondary@example.org", "primary": False, "verified": True},
                    {"email": profile["email"], "primary": True, "verified": profile["verified"]},
                ],
            )
        else:
            self._json(404, {"error": "not_found"})


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

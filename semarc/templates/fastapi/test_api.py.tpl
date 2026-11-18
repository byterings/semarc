"""Replays tests/api_scenario.json against the application with a fresh SQLite database.

Usage: pytest
"""
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["DB_CONNECTION"] = "sqlite"
os.environ["DB_DATABASE"] = str(Path(tempfile.mkdtemp()) / "test.sqlite")
os.environ.setdefault("JWT_SECRET", "semarc-test-secret-semarc-test-secret")
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "admin@example.com"
os.environ["MAIL_DRIVER"] = "memory"
os.environ["RATE_LIMIT_STORE"] = "local"
SCENARIO = json.loads((ROOT / "tests" / "api_scenario.json").read_text(encoding="utf-8"))
os.environ.update(SCENARIO.get("env", {}))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

MISSING = object()


def dig(data, path: str):
    for key in path.split("."):
        if not isinstance(data, dict) or key not in data:
            return MISSING
        data = data[key]
    return data


def resolve(value, variables: dict):
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return variables.get(value["$ref"])
        return {key: resolve(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, variables) for item in value]
    return value


def read_mail(step: dict) -> str:
    from core.mailer import outbox

    mail = step["mail"]
    for message in reversed(outbox):
        if message["to"] == mail["to"] and message["subject"] == mail["subject"]:
            match = re.search(mail["pattern"], message["body"])
            if match:
                return match.group(1)
    raise AssertionError(f"{step['name']}: no email {mail['subject']!r} to {mail['to']} matching {mail['pattern']}")


def test_api_scenario() -> None:
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    client = TestClient(app, raise_server_exceptions=False)
    variables: dict = {}
    session = SCENARIO.get("session")  # AUTH SESSION: credentials are cookies plus a CSRF header
    session_cookies: dict = {}

    for step in SCENARIO["steps"]:
        if "external" in step:
            continue  # needs an external service (see the scenario description)
        if "mail" in step:
            variables[step["mail"]["save"]] = read_mail(step)
            continue
        path = re.sub(r"\$\{(\w+)\}", lambda match: str(variables.get(match.group(1), "")), step["path"])
        headers = dict(step.get("headers", {}))
        credential = None
        if step.get("auth"):
            name = step.get("auth_as", "token")
            credential = (session_cookies.get(name, ""), variables.get(name, ""))
        if "token" in step:
            credential = (step["token"], step["token"])
        if credential is not None and session is None:
            headers["Authorization"] = f"Bearer {credential[1]}"
        elif credential is not None:
            headers["Cookie"] = f"{session['cookie']}={credential[0]}"
            if step["method"] not in {"GET", "HEAD", "OPTIONS"} and step.get("csrf", True):
                headers[session["csrf_header"]] = str(credential[1])
        kwargs = {"headers": headers}
        if "body" in step:
            kwargs["json"] = resolve(step["body"], variables)

        client.cookies.clear()  # every step sends its own credentials
        response = client.request(step["method"], path, **kwargs)
        is_json = response.headers.get("content-type", "").startswith("application/json")
        payload = response.json() if is_json and response.content else None
        label = f"{step['name']} ({step['method']} {path}): {response.text[:300]}"

        expected = step["expect"] if isinstance(step["expect"], list) else [step["expect"]]
        assert response.status_code in expected, label
        for name, value in step.get("expect_headers", {}).items():
            assert response.headers.get(name) == value, f"{label}\n  header {name}: expected {value!r}"
        for json_path, expected in step.get("equals", {}).items():
            expected = resolve(expected, variables)
            actual = dig(payload, json_path)
            assert actual is not MISSING and actual == expected and type(actual) is type(expected), (
                f"{label}\n  {json_path}: expected {expected!r}, got {actual!r}"
            )
        for json_path in step.get("absent", []):
            assert dig(payload, json_path) is MISSING, f"{label}\n  {json_path} must not be present"
        issued = None
        for cookie in response.headers.get_list("set-cookie") if session else []:
            if cookie.startswith(session["cookie"] + "="):
                attributes = cookie.lower()
                assert "httponly" in attributes and "samesite=lax" in attributes, f"{label}\n  insecure session cookie: {cookie}"
                issued = cookie.split(";")[0].split("=", 1)[1]
        for name, json_path in step.get("save", {}).items():
            variables[name] = dig(payload, json_path)
            if issued is not None and json_path.endswith("csrf_token"):
                session_cookies[name] = issued

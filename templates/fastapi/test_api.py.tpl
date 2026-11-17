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


def test_api_scenario() -> None:
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    scenario = json.loads((ROOT / "tests" / "api_scenario.json").read_text(encoding="utf-8"))
    client = TestClient(app, raise_server_exceptions=False)
    variables: dict = {}

    for step in scenario["steps"]:
        path = re.sub(r"\$\{(\w+)\}", lambda match: str(variables.get(match.group(1), "")), step["path"])
        headers = {}
        if step.get("auth"):
            headers["Authorization"] = f"Bearer {variables.get('token', '')}"
        if "token" in step:
            headers["Authorization"] = f"Bearer {step['token']}"
        kwargs = {"headers": headers}
        if "body" in step:
            kwargs["json"] = resolve(step["body"], variables)

        response = client.request(step["method"], path, **kwargs)
        is_json = response.headers.get("content-type", "").startswith("application/json")
        payload = response.json() if is_json and response.content else None
        label = f"{step['name']} ({step['method']} {path}): {response.text[:300]}"

        assert response.status_code == step["expect"], label
        for json_path, expected in step.get("equals", {}).items():
            expected = resolve(expected, variables)
            actual = dig(payload, json_path)
            assert actual is not MISSING and actual == expected and type(actual) is type(expected), (
                f"{label}\n  {json_path}: expected {expected!r}, got {actual!r}"
            )
        for json_path in step.get("absent", []):
            assert dig(payload, json_path) is MISSING, f"{label}\n  {json_path} must not be present"
        for name, json_path in step.get("save", {}).items():
            variables[name] = dig(payload, json_path)

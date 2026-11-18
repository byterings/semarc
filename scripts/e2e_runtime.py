#!/usr/bin/env python3
"""End-to-end runtime verification for generated projects.

For each requested (example, target, database) combination this script:

1. compiles the semantic source with the database engine overridden,
2. starts the generated project with `docker compose up --build`,
3. waits for GET /health,
4. replays the generated tests/api_scenario.json over real HTTP, reading email from the
   project's Mailpit and, for OAuth projects, signing in through scripts/oauth_mock.py,
5. tears the stack down (containers and volumes).

Usage:
    python3 scripts/e2e_runtime.py                       # every example, target and database
    python3 scripts/e2e_runtime.py --targets php --databases sqlite examples/blog_api.sem
    python3 scripts/e2e_runtime.py --keep                # leave stacks running for inspection

Requires Docker with the compose plugin. It is not part of the offline unit
test suite because it builds images and downloads dependencies.
"""
import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semarc.compiler.pipeline import compile_semantic_file  # noqa: E402
from semarc.validator.validator import SemanticValidationError  # noqa: E402

TARGETS = ["php", "fastapi", "nestjs"]
DATABASES = {"sqlite": "SQLITE", "mysql": "MYSQL", "postgresql": "POSTGRESQL"}
MISSING = object()
MOCK_IMAGE = "python:3.12-slim"
MOCK_PORT = 9000


class ScenarioFailure(AssertionError):
    pass


class ScenarioClient:
    """Replays an api_scenario.json document against a live base URL."""

    def __init__(self, base_url: str, mail_url: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.mail_url = mail_url

    def run(self, scenario: dict, verbose: bool = False) -> int:
        variables: dict = {}
        session = scenario.get("session")  # AUTH SESSION: cookie per saved credential plus a CSRF header
        session_cookies: dict = {}
        for step in scenario["steps"]:
            if "mail" in step:
                variables[step["mail"]["save"]] = self._read_mail(step)
                if verbose:
                    print(f"    PASS {step['name']}")
                continue
            path = re.sub(r"\$\{(\w+)\}", lambda match: str(variables.get(match.group(1), "")), step["path"])
            headers = {"Accept": "application/json", **step.get("headers", {})}
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
            body = None
            if "body" in step:
                body = json.dumps(self._resolve(step["body"], variables)).encode()
                headers["Content-Type"] = "application/json"

            status, payload, raw, response_headers = self._request(step["method"], path, headers, body)
            problems = []
            expected = step["expect"] if isinstance(step["expect"], list) else [step["expect"]]
            if status not in expected:
                problems.append(f"expected status {step['expect']}, got {status}")
            for name, value in step.get("expect_headers", {}).items():
                if response_headers.get(name) != value:
                    problems.append(f"header {name}: expected {value!r}, got {response_headers.get(name)!r}")
            for json_path, expected in step.get("equals", {}).items():
                expected = self._resolve(expected, variables)
                actual = self._dig(payload, json_path)
                if actual is MISSING or actual != expected or type(actual) is not type(expected):
                    shown = "nothing" if actual is MISSING else json.dumps(actual)
                    problems.append(f"{json_path}: expected {json.dumps(expected)}, got {shown}")
            for json_path in step.get("absent", []):
                if self._dig(payload, json_path) is not MISSING:
                    problems.append(f"{json_path} must not be present")
            if problems:
                details = "\n".join(f"  - {problem}" for problem in problems)
                raise ScenarioFailure(f"{step['name']} ({step['method']} {path})\n{details}\n  response: {raw[:500]}")

            issued = None
            for cookie in (response_headers.get_all("Set-Cookie") or []) if session else []:
                if cookie.startswith(session["cookie"] + "="):
                    attributes = cookie.lower()
                    if "httponly" not in attributes or "samesite=lax" not in attributes:
                        raise ScenarioFailure(f"{step['name']}: session cookie must be HttpOnly and SameSite=Lax: {cookie}")
                    issued = cookie.split(";")[0].split("=", 1)[1]
            for name, json_path in step.get("save", {}).items():
                variables[name] = self._dig(payload, json_path)
                if issued is not None and json_path.endswith("csrf_token"):
                    session_cookies[name] = issued
            if verbose:
                print(f"    PASS {step['name']}")
        return len(scenario["steps"])

    def _request(self, method: str, path: str, headers: dict, body: bytes | None) -> tuple[int, object, str, object]:
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status, raw, response_headers = response.status, response.read().decode(), response.headers
        except urllib.error.HTTPError as error:
            status, raw, response_headers = error.code, error.read().decode(), error.headers
        payload = None
        if raw and "json" in response_headers.get("Content-Type", ""):
            payload = json.loads(raw)
        return status, payload, raw, response_headers

    def _read_mail(self, step: dict) -> str:
        """Reads the newest matching email from Mailpit's API."""
        mail = step["mail"]
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            with urllib.request.urlopen(f"{self.mail_url}/api/v1/messages?limit=100", timeout=10) as response:
                messages = json.loads(response.read().decode())["messages"]
            for message in messages:
                recipients = [item["Address"] for item in message.get("To", [])]
                if mail["to"] in recipients and message["Subject"] == mail["subject"]:
                    with urllib.request.urlopen(f"{self.mail_url}/api/v1/message/{message['ID']}", timeout=10) as response:
                        body = json.loads(response.read().decode())["Text"]
                    match = re.search(mail["pattern"], body)
                    if match:
                        return match.group(1)
            time.sleep(0.5)
        raise ScenarioFailure(f"{step['name']}: no email {mail['subject']!r} to {mail['to']} in Mailpit")

    def _resolve(self, value, variables: dict):
        if isinstance(value, dict):
            if set(value) == {"$ref"}:
                return variables.get(value["$ref"])
            return {key: self._resolve(item, variables) for key, item in value.items()}
        if isinstance(value, list):
            return [self._resolve(item, variables) for item in value]
        return value

    def _dig(self, data, path: str):
        for key in path.split("."):
            if not isinstance(data, dict) or key not in data:
                return MISSING
            data = data[key]
        return data


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_health(base_url: str, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(base_url + "/health", timeout=5) as response:
                if response.status == 200:
                    return
                last_error = f"status {response.status}"
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            last_error = str(error)
        time.sleep(2)
    raise TimeoutError(f"{base_url}/health did not become healthy within {timeout}s ({last_error})")


def with_database(source: str, engine: str) -> str:
    lines = [line for line in source.splitlines() if not line.strip().startswith("DATABASE ")]
    insert_at = next((index + 1 for index, line in enumerate(lines) if line.startswith("PROJECT ")), 0)
    lines.insert(insert_at, f"\nDATABASE {engine}")
    return "\n".join(lines) + "\n"


def compose(
    project_dir: Path, name: str, port: int, *args: str, capture: bool = False, mail_port: int = 0, extra_env: dict | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", "-p", name, *args],
        cwd=project_dir,
        env={
            **_base_env(),
            "APP_PORT": str(port),
            "MAIL_UI_PORT": str(mail_port or free_port()),
            "BOOTSTRAP_ADMIN_EMAIL": "admin@example.com",
            **(extra_env or {}),
        },
        capture_output=capture,
        text=True,
        check=False,
    )


def oauth_env(scenario: dict) -> dict:
    """Scenario settings plus OAUTH_<PROVIDER>_ENDPOINT pointing every provider at the mock."""
    env = dict(scenario.get("env", {}))
    for key in list(env):
        if key.startswith("OAUTH_") and key.endswith("_CLIENT_ID"):
            env[key.removesuffix("_CLIENT_ID") + "_ENDPOINT"] = f"http://oauth-mock:{MOCK_PORT}"
    return env


def start_oauth_mock(name: str) -> str:
    """Runs scripts/oauth_mock.py on the project network as host oauth-mock."""
    container = f"{name}-oauth-mock"
    subprocess.run(["docker", "rm", "-f", container], capture_output=True, check=False)
    result = subprocess.run(
        [
            "docker", "run", "-d", "--rm", "--name", container,
            "--network", f"{name}_default", "--network-alias", "oauth-mock",
            "-v", f"{ROOT / 'scripts' / 'oauth_mock.py'}:/oauth_mock.py:ro",
            MOCK_IMAGE, "python", "/oauth_mock.py", str(MOCK_PORT),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ScenarioFailure(f"could not start the OAuth mock provider: {result.stderr.strip()}")
    return container


def _base_env() -> dict:
    import os

    return dict(os.environ)


def run_case(source_path: Path, target: str, database: str, keep: bool, verbose: bool, workdir: Path) -> tuple[bool | None, str]:
    label = f"{source_path.stem} / {target} / {database}"
    case_dir = workdir / f"{source_path.stem}-{target}-{database}"
    source_copy = case_dir / source_path.name
    output_dir = case_dir / "project"
    case_dir.mkdir(parents=True, exist_ok=True)
    source_copy.write_text(with_database(source_path.read_text(encoding="utf-8"), DATABASES[database]), encoding="utf-8")

    try:
        compile_semantic_file(source_copy, target_override=target, output_dir=str(output_dir), force_output=True)
    except SemanticValidationError as error:
        reason = str(error).replace("[Semantic Error]", "").strip().splitlines()[0]
        return None, f"{label}: not applicable ({reason})"
    scenario_file = next(path for path in [output_dir / "tests" / "api_scenario.json", output_dir / "test" / "api_scenario.json"] if path.exists())
    scenario = json.loads(scenario_file.read_text(encoding="utf-8"))

    port = free_port()
    name = re.sub(r"[^a-z0-9]", "", f"semarce2e{source_path.stem}{target}{database}".lower())
    base_url = f"http://127.0.0.1:{port}"
    print(f"[{label}] building and starting on port {port}")
    mail_port = free_port()
    extra_env = oauth_env(scenario)
    needs_mock = any(step.get("external") == "oauth" for step in scenario["steps"])
    mock = None
    started = compose(
        output_dir, name, port, "up", "--build", "-d", "--wait-timeout", "300", capture=True, mail_port=mail_port, extra_env=extra_env
    )
    try:
        if started.returncode != 0:
            return False, f"{label}: docker compose up failed\n{started.stdout[-2000:]}\n{started.stderr[-2000:]}"
        if needs_mock:
            mock = start_oauth_mock(name)
        wait_for_health(base_url, timeout=240)
        steps = ScenarioClient(base_url, f"http://127.0.0.1:{mail_port}").run(scenario, verbose=verbose)
        return True, f"{label}: {steps} scenario steps passed"
    except (ScenarioFailure, TimeoutError) as error:
        logs = compose(output_dir, name, port, "logs", "--tail", "60", capture=True)
        return False, f"{label}: {error}\n--- logs ---\n{logs.stdout[-3000:]}"
    finally:
        if not keep:
            if mock:
                subprocess.run(["docker", "rm", "-f", mock], capture_output=True, check=False)
            compose(output_dir, name, port, "down", "-v", "--remove-orphans", capture=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", help="Semantic sources (default: examples/*.sem)")
    parser.add_argument("--targets", nargs="+", choices=TARGETS, default=TARGETS)
    parser.add_argument("--databases", nargs="+", choices=sorted(DATABASES), default=sorted(DATABASES))
    parser.add_argument("--keep", action="store_true", help="Keep stacks and generated projects for inspection")
    parser.add_argument("--verbose", action="store_true", help="Print every scenario step")
    args = parser.parse_args()

    if shutil.which("docker") is None:
        print("docker is required for end-to-end runtime verification")
        return 2

    sources = [Path(source) for source in args.sources] or sorted((ROOT / "examples").glob("*.sem"))
    workdir = Path(tempfile.mkdtemp(prefix="semarc-e2e-"))
    results = []
    try:
        for source in sources:
            for target in args.targets:
                for database in args.databases:
                    ok, message = run_case(source, target, database, args.keep, args.verbose, workdir)
                    results.append(ok)
                    print({True: "PASS ", False: "FAIL ", None: "SKIP "}[ok] + message, flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)
        else:
            print(f"Generated projects kept in {workdir}")

    passed = results.count(True)
    failed = results.count(False)
    skipped = results.count(None)
    print(f"\nEnd-to-end runtime verification: {passed} passed, {failed} failed, {skipped} not applicable")
    return 0 if failed == 0 and passed > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

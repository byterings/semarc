#!/usr/bin/env python3
"""Runs the test suite that SEMARC generates inside each project.

For every specification and target this script generates the project and runs the
project's own runner (php tests/run.php, pytest, npm test) in the target's official
Docker image. It is faster than scripts/e2e_runtime.py because it needs no database
container; e2e_runtime.py remains the check against live MySQL and PostgreSQL stacks.

Usage:
    python3 scripts/project_tests.py examples/blog_api.sem
    python3 scripts/project_tests.py tests/fixtures/*.sem --targets php nestjs
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semarc.compiler.pipeline import compile_semantic_file  # noqa: E402
from semarc.validator.validator import SemanticValidationError  # noqa: E402

CACHE = Path(os.environ.get("SEMARC_DEV_CACHE", Path.home() / ".cache" / "semarc-dev"))
RUNNERS = {
    "php": ("php:8.3-cli", "php tests/run.php", {}),
    "fastapi": (
        "python:3.12-slim",
        "pip install -q --user --no-warn-script-location -r requirements.txt && python -m pytest -q -p no:cacheprovider",
        {"PYTHONDONTWRITEBYTECODE": "1", "PIP_CACHE_DIR": "/cache/pip"},
    ),
    "nestjs": (
        "node:24-bookworm-slim",
        "npm install --no-audit --no-fund --loglevel=error && npx tsc --noEmit -p tsconfig.json && npm test",
        {"npm_config_cache": "/cache/npm"},
    ),
}


def run(source: Path, target: str, workdir: Path, verbose: bool) -> tuple[bool | None, str]:
    output = workdir / f"{source.stem}-{target}"
    try:
        compile_semantic_file(source, target_override=target, output_dir=str(output), force_output=True)
    except SemanticValidationError as error:
        return None, str(error).replace("[Semantic Error]", "").strip().splitlines()[0]

    image, command, environment = RUNNERS[target]
    (CACHE / "pip").mkdir(parents=True, exist_ok=True)
    (CACHE / "npm").mkdir(parents=True, exist_ok=True)
    docker = ["docker", "run", "--rm", "-v", f"{output}:/app", "-v", f"{CACHE}:/cache", "-w", "/app", "-e", "HOME=/tmp"]
    if hasattr(os, "getuid"):
        docker += ["-u", f"{os.getuid()}:{os.getgid()}"]
    for key, value in environment.items():
        docker += ["-e", f"{key}={value}"]
    result = subprocess.run([*docker, image, "sh", "-c", command], capture_output=True, text=True, check=False)
    log = result.stdout + result.stderr
    if verbose or result.returncode != 0:
        return result.returncode == 0, log[-4000:]
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+", help="Semantic sources")
    parser.add_argument("--targets", nargs="+", choices=sorted(RUNNERS), default=sorted(RUNNERS))
    parser.add_argument("--keep", action="store_true", help="Keep generated projects")
    parser.add_argument("--verbose", action="store_true", help="Print runner output for passing projects too")
    args = parser.parse_args()

    if shutil.which("docker") is None:
        print("docker is required")
        return 2

    workdir = Path(tempfile.mkdtemp(prefix="semarc-project-tests-"))
    results = []
    try:
        for source in map(Path, args.sources):
            for target in args.targets:
                ok, log = run(source.resolve(), target, workdir, args.verbose)
                results.append(ok)
                label = {True: "PASS", False: "FAIL", None: "SKIP"}[ok]
                print(f"{label} {source.stem} / {target}" + (f": {log}" if ok is None else ""), flush=True)
                if log and ok is not None:
                    print(log)
    finally:
        if args.keep:
            print(f"Generated projects kept in {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)

    failed = results.count(False)
    print(f"\nProject tests: {results.count(True)} passed, {failed} failed, {results.count(None)} not applicable")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

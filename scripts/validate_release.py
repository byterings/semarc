#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    ("Unit Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_semarc.py"]),
    ("Integration Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests/integration"]),
    ("Golden Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests/golden"]),
    ("Regression Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests/regression"]),
    ("Release Tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests/release"]),
    (
        "Compile Checks",
        [
            sys.executable,
            "-m",
            "compileall",
            "main.py",
            "architecture",
            "compiler",
            "generator",
            "lexer",
            "parser",
            "validator",
            "tests",
            "ast_loader.py",
        ],
    ),
]


def main() -> int:
    failures = []
    for label, command in CHECKS:
        print(f"[{label}]")
        result = subprocess.run(command, cwd=ROOT, text=True, check=False)
        if result.returncode != 0:
            failures.append(label)
            print(f"{label}: FAIL")
        else:
            print(f"{label}: PASS")

    if failures:
        print("\nRelease Validation: FAIL")
        print("Failed checks: " + ", ".join(failures))
        return 1

    print("\nRelease Validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

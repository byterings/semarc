"""Compile a semantic architecture file: python3 main.py app.sem [--target T] [--output DIR] [--force] [--debug].

Equivalent to `semarc build`. See semarc/compiler/cli.py for every command.
"""
from semarc.compiler.cli import legacy_main
from semarc.compiler.pipeline import compile_semantic_file

__all__ = ["compile_semantic_file"]


if __name__ == "__main__":
    raise SystemExit(legacy_main())

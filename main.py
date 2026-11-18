"""Compile a semantic architecture file: python3 main.py app.sem [--target T] [--output DIR] [--force] [--debug].

Equivalent to `semarc build`. See compiler/cli.py for every command.
"""
from compiler.cli import legacy_main
from compiler.pipeline import compile_semantic_file

__all__ = ["compile_semantic_file"]


if __name__ == "__main__":
    raise SystemExit(legacy_main())

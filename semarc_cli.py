"""Entry point of the `semarc` console command.

SEMARC's packages use generic top-level names (ast, parser, compiler, ...), so they are
not installed into site-packages. The command runs SEMARC from the checkout it was
installed from, which requires an editable install: pip install -e /path/to/semarc
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    if not (ROOT / "compiler" / "cli.py").is_file():
        print("semarc must be installed in editable mode from a SEMARC checkout: pip install -e /path/to/semarc", file=sys.stderr)
        return 2
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from compiler.cli import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())

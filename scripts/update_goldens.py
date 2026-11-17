#!/usr/bin/env python3
"""Regenerates golden snapshots after an intentional generator change.

Review the resulting git diff before committing: goldens exist to make
generator output changes explicit.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.golden.test_golden_generators import GOLDEN_SOURCE, GoldenGeneratorTests  # noqa: E402
from tests.support import compile_source, generated_file_map  # noqa: E402


def main() -> int:
    for target, snapshots in GoldenGeneratorTests.SNAPSHOTS.items():
        golden_dir = ROOT / "tests" / "golden" / target
        golden_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            source = GOLDEN_SOURCE.replace("TARGET PHP", f"TARGET {target.upper()}")
            context = compile_source(source, tmpdir, target, generate=True)
            output_files = generated_file_map(Path(context.output_dir))

        (golden_dir / "manifest.txt").write_text("\n".join(sorted(output_files)) + "\n", encoding="utf-8")
        for generated_path, golden_name in snapshots.items():
            (golden_dir / golden_name).write_text(output_files[generated_path], encoding="utf-8")
        print(f"Updated goldens for {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

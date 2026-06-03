import tempfile
import unittest
from pathlib import Path

from tests.support import ROOT, GeneratorValidationSuite, compile_source, generated_file_map


GOLDEN_SOURCE = """PROJECT GoldenAPI

TARGET PHP

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING
    name STRING

ROUTE POST /login
ROUTE GET /users
"""


class GoldenGeneratorTests(unittest.TestCase):
    SNAPSHOTS = {
        "php": {
            "routes.php": "routes.php",
            "models/User.php": "User.php",
        },
        "fastapi": {
            "main.py": "main.py",
            "models/user.py": "user.py",
        },
        "nestjs": {
            "src/modules/users/users.controller.ts": "users.controller.ts",
            "src/modules/users/users.service.ts": "users.service.ts",
        },
    }

    def test_generator_outputs_match_golden_manifests_and_snapshots(self):
        for target in ["php", "fastapi", "nestjs"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmpdir:
                source = GOLDEN_SOURCE.replace("TARGET PHP", f"TARGET {target.upper()}")
                context = compile_source(source, tmpdir, target, generate=True)
                output_files = generated_file_map(Path(context.output_dir))
                golden_dir = ROOT / "tests" / "golden" / target

                expected_manifest = (golden_dir / "manifest.txt").read_text(encoding="utf-8").splitlines()
                self.assertEqual(sorted(output_files), expected_manifest)

                for generated_path, golden_name in self.SNAPSHOTS[target].items():
                    self.assertEqual(
                        output_files[generated_path],
                        (golden_dir / golden_name).read_text(encoding="utf-8"),
                    )

                GeneratorValidationSuite().validate(context, target)

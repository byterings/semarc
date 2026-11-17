import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from compiler.passes.generation_pass import GenerationBlockedError
from generator.output_directory import OutputDirectory, OutputDirectoryError
from tests.support import ROOT, compile_source
from validator.validator import SemanticValidationError


SOURCE = """PROJECT CliDemo

DATABASE MYSQL

MODEL Post
    title STRING

ROUTE GET /posts
"""


class TargetSelectionTests(unittest.TestCase):
    def test_unimplemented_source_target_is_rejected(self):
        for target in ["LARAVEL", "NODE", "DJANGO"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmpdir:
                source = SOURCE.replace("DATABASE MYSQL", f"TARGET {target}\n\nDATABASE MYSQL")
                with self.assertRaises(SemanticValidationError) as raised:
                    compile_source(source, tmpdir, None, generate=False)
                self.assertIn(f"Unsupported target profile: {target}", str(raised.exception))
                self.assertIn("available: FASTAPI, NESTJS, PHP", str(raised.exception))

    def test_unimplemented_target_override_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(SemanticValidationError) as raised:
                compile_source(SOURCE, tmpdir, "laravel", generate=False)
            self.assertIn("Unsupported target profile: LARAVEL", str(raised.exception))


class OutputDirectoryTests(unittest.TestCase):
    def test_foreign_non_empty_directory_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "existing"
            output.mkdir()
            keep = output / "notes.txt"
            keep.write_text("user data", encoding="utf-8")

            with self.assertRaises(OutputDirectoryError):
                OutputDirectory().prepare(output)
            self.assertTrue(keep.exists())

    def test_force_replaces_foreign_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "existing"
            output.mkdir()
            (output / "notes.txt").write_text("user data", encoding="utf-8")

            OutputDirectory().prepare(output, force=True)
            self.assertEqual(list(output.iterdir()), [])

    def test_regeneration_removes_stale_files_from_previous_target(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = compile_source(SOURCE, tmpdir, "nestjs", generate=True)
            output = Path(first.output_dir)
            self.assertTrue((output / "package.json").exists())

            compile_source(SOURCE, tmpdir, "php", generate=True)
            self.assertFalse((output / "package.json").exists())
            self.assertFalse((output / "src").exists())
            self.assertTrue((output / "routes.php").exists())

    def test_cli_writes_to_requested_output_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "app.sem"
            source.write_text(SOURCE, encoding="utf-8")
            output = Path(tmpdir) / "generated"

            result = subprocess.run(
                [sys.executable, str(ROOT / "main.py"), str(source), "--output", str(output), "--target", "fastapi"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((output / "generator_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["generator"], "fastapi")


class DiagnosticBlockingTests(unittest.TestCase):
    def test_diagnostic_errors_block_generation(self):
        source = SOURCE + "\nAUTH JWT\nAUTH SESSION\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(GenerationBlockedError) as raised:
                compile_source(source, tmpdir, "php", generate=True)
            self.assertIn("AUTH002", str(raised.exception))
            self.assertFalse((Path(tmpdir) / "out").exists())


class PackageNameTests(unittest.TestCase):
    def test_nestjs_package_name_is_kebab_case(self):
        source = SOURCE.replace("PROJECT CliDemo", "PROJECT BlogAPI")
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "nestjs", generate=True)
            package = json.loads((Path(context.output_dir) / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(package["name"], "blog-api")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from generator.targets import TargetLoader, TargetRegistry
from tests.support import GeneratorValidationSuite, ROOT, compile_source


SOURCE = """PROJECT TemplateDemo

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING

ROUTE POST /login
ROUTE GET /users
"""


class ProjectTemplateFoundationTests(unittest.TestCase):
    def test_builtin_targets_are_registered(self):
        registry = TargetRegistry.builtins()

        self.assertEqual(registry.get("php").language, "PHP")
        self.assertEqual(registry.get("fastapi").language, "Python")
        self.assertEqual(registry.get("nestjs").language, "TypeScript")

    def test_target_loader_reads_project_template_metadata(self):
        for target in ["php", "fastapi", "nestjs"]:
            with self.subTest(target=target):
                metadata = TargetLoader().load(ROOT / "generator" / target / "project_template" / "target.yaml")

                self.assertEqual(metadata.name, target)
                self.assertTrue(metadata.language)
                self.assertTrue(metadata.description)

    def test_runnable_project_files_are_generated_for_all_targets(self):
        for target in ["php", "fastapi", "nestjs"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmpdir:
                context = compile_source(SOURCE, tmpdir, target, generate=True)
                output_dir = Path(context.output_dir)

                GeneratorValidationSuite().validate(context, target)
                self.assertTrue((output_dir / "README.md").exists())
                self.assertTrue((output_dir / ".env.example").exists())
                self.assertTrue((output_dir / "Dockerfile").exists())
                self.assertTrue((output_dir / "docker-compose.yml").exists())
                self.assertTrue((output_dir / "generator_manifest.json").exists())

                manifest = json.loads((output_dir / "generator_manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["generator"], target)
                self.assertEqual(manifest["semarc_version"], "0.12.0")
                self.assertEqual(manifest["project"], "TemplateDemo")

import tempfile
import unittest
from pathlib import Path

from tests.support import ROOT, GeneratorValidationSuite, compile_file

FIXTURES = sorted((ROOT / "tests" / "fixtures").glob("*.sem"))


class EdgeCaseGenerationTests(unittest.TestCase):
    """Specifications that exercise naming and parameter corner cases on every target."""

    def test_edge_case_fixtures_generate_valid_projects(self):
        self.assertTrue(FIXTURES)
        for fixture in FIXTURES:
            for target in ["php", "fastapi", "nestjs"]:
                with self.subTest(fixture=fixture.name, target=target), tempfile.TemporaryDirectory() as tmpdir:
                    context = compile_file(fixture, Path(tmpdir) / "out", target)
                    GeneratorValidationSuite().validate(context, target)

    def test_protected_route_with_user_id_parameter_compiles_in_fastapi(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_file(ROOT / "tests" / "fixtures" / "edge_auth.sem", Path(tmpdir) / "out", "fastapi")
            router = (Path(context.output_dir) / "routers" / "blog_post.py").read_text(encoding="utf-8")
        self.assertIn("def list_blog_posts_by_user(user_id: int,", router)
        self.assertIn("current_user: int = Depends(current_user_id)", router)


if __name__ == "__main__":
    unittest.main()

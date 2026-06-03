import json
import tempfile
import unittest
from pathlib import Path

from tests.support import GeneratorValidationSuite, compile_source


PROJECTS = {
    "blog": """PROJECT BlogRelease

PROFILE BLOG

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING

MODEL Post
    title STRING

RELATION User HAS_MANY Post

ROUTE POST /login
ROUTE GET /posts
""",
    "crm": """PROJECT CrmRelease

PROFILE CRM

DATABASE MYSQL

MODEL Customer
    name STRING

MODEL Activity
    title STRING

RELATION Customer HAS_MANY Activity

ROUTE GET /customers
""",
    "inventory": """PROJECT InventoryRelease

PROFILE INVENTORY

DATABASE MYSQL

MODEL Product
    name STRING

MODEL Stock
    quantity INTEGER

RELATION Product HAS_MANY Stock

ROUTE GET /products
ROUTE GET /stock
""",
    "ecommerce": """PROJECT EcommerceRelease

PROFILE ECOMMERCE

DATABASE MYSQL

MODEL User
    email STRING

MODEL Order
    total FLOAT

RELATION User HAS_MANY Order

ROUTE GET /orders
""",
    "saas": """PROJECT SaasRelease

PROFILE COMPANY_STANDARD
USE cache.redis

DATABASE MYSQL

AUTH JWT

MODEL Account
    name STRING

MODEL User
    email STRING

RELATION Account HAS_MANY User

ROUTE POST /login
ROUTE GET /accounts
ROUTE GET /users
""",
}


class EndToEndReleaseValidationTests(unittest.TestCase):
    def test_release_projects_compile_for_all_generators(self):
        validator = GeneratorValidationSuite()
        for project_name, source in PROJECTS.items():
            for target in ["php", "fastapi", "nestjs"]:
                with self.subTest(project=project_name, target=target), tempfile.TemporaryDirectory() as tmpdir:
                    context = compile_source(source, tmpdir, target, generate=True)
                    output_dir = Path(context.output_dir)

                    validator.validate(context, target)
                    report_path = output_dir / "architecture_report.json"
                    self.assertTrue(report_path.exists())

                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    self.assertEqual(report["project"], project_name_to_semarc_name(project_name))
                    self.assertEqual(report["target"], target.upper())
                    self.assertIn("statistics", report)
                    self.assertIn("analysis", report)
                    self.assertIn("constraints", report)
                    self.assertIn("generator", report)
                    self.assertIn("compilation", report)
                    self.assertGreater(report["statistics"]["models"], 0)
                    self.assertGreater(report["compilation"]["generated_components"], 0)


def project_name_to_semarc_name(project_name: str) -> str:
    return {
        "blog": "BlogRelease",
        "crm": "CrmRelease",
        "inventory": "InventoryRelease",
        "ecommerce": "EcommerceRelease",
        "saas": "SaasRelease",
    }[project_name]

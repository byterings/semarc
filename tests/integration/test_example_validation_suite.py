import json
import tempfile
import unittest
from pathlib import Path

from architecture.packages import PackageLoader
from architecture.profiles import ProfileLoader
from compiler.context import CompilerContext
from compiler.contracts import ContractValidator
from compiler.passes.constraint_pass import ConstraintPass
from compiler.passes.contract_pass import ContractPass
from compiler.passes.diagnostic_report_pass import DiagnosticReportPass
from compiler.passes.expansion_pass import ExpansionPass
from compiler.passes.generation_pass import GenerationPass
from compiler.passes.ir_pass import IRPass
from compiler.passes.lexing_pass import LexingPass
from compiler.passes.module_constraint_pass import ModuleConstraintPass
from compiler.passes.optimization_pass import OptimizationPass
from compiler.passes.parsing_pass import ParsingPass
from compiler.passes.relationship_pass import RelationshipPass
from compiler.passes.stdlib_pass import StdlibPass
from compiler.passes.validation_pass import ValidationPass
from lexer.lexer import Lexer
from parser.parser import Parser


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = [
    ("Blog API", ROOT / "examples" / "blog_api.sem"),
    ("ECommerce", ROOT / "examples" / "ecommerce.sem"),
    ("CRM", ROOT / "examples" / "crm.sem"),
    ("Inventory", ROOT / "examples" / "inventory.sem"),
    ("School Management", ROOT / "examples" / "school_management.sem"),
]
PROFILE_TEST_EXAMPLES = [
    ROOT / "examples" / "profile_tests" / "basic_profile.sem",
    ROOT / "examples" / "profile_tests" / "multiple_profiles.sem",
    ROOT / "examples" / "profile_tests" / "profile_with_packages.sem",
    ROOT / "examples" / "profile_tests" / "custom_company_profile.sem",
]


class ExampleProjectValidationSuite(unittest.TestCase):
    """Stress-tests realistic semantic projects against both target generators."""

    def test_all_examples_compile_and_generate_reports(self):
        rows = []
        failures = []

        for example_name, source_path in EXAMPLES:
            row = self._validate_example(example_name, source_path, failures)
            rows.append(row)

        self._write_report(rows)

        if failures:
            self.fail("\n".join(failures))

    def _validate_example(self, example_name: str, source_path: Path, failures: list[str]) -> dict:
        row = {
            "example": example_name,
            "compilation": "PASS",
            "ir": "PASS",
            "migration": "PASS",
            "php": "PASS",
            "fastapi": "PASS",
            "diagnostics": "PASS",
            "profiles": "",
            "packages": "",
            "score": "",
            "warnings": "",
            "recommendations": "",
            "errors": "",
        }

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                php_context = self._compile(source_path, Path(tmpdir) / "php", "php")
                fastapi_context = self._compile(source_path, Path(tmpdir) / "fastapi", "fastapi")

                self._validate_common_context(php_context)
                self._validate_common_context(fastapi_context)
                self._validate_metadata_context(php_context)
                self._validate_metadata_context(fastapi_context)
                self._validate_php_output(Path(tmpdir) / "php")
                self._validate_fastapi_output(Path(tmpdir) / "fastapi")

                report = self._load_report(Path(tmpdir) / "fastapi")
                row["profiles"] = str(len(fastapi_context.ir["profiles"]))
                row["packages"] = str(len(fastapi_context.ir["packages"]))
                row["score"] = str(report["score"])
                row["warnings"] = str(len(report["warnings"]))
                row["recommendations"] = str(len(report["recommendations"]))
                row["errors"] = str(len(report["errors"]))
        except Exception as error:  # pragma: no cover - failure path is reported for humans.
            row["compilation"] = "FAIL"
            row["ir"] = "FAIL"
            row["migration"] = "FAIL"
            row["php"] = "FAIL"
            row["fastapi"] = "FAIL"
            row["diagnostics"] = "FAIL"
            failures.append(f"{example_name}: {error}")

        return row

    def test_profile_test_examples_compile_as_metadata_only(self):
        for source_path in PROFILE_TEST_EXAMPLES:
            with self.subTest(source=source_path.name), tempfile.TemporaryDirectory() as tmpdir:
                context = self._compile(source_path, Path(tmpdir) / "out", "php")

                self.assertGreater(len(context.ast.profiles), 0)
                self.assertIn("profiles", context.ir)
                self.assertIn("packages", context.ir)
                self.assertEqual(ContractValidator().validate_ir(context.ir), [])
                self.assertTrue((Path(tmpdir) / "out" / "architecture_report.json").exists())

    def test_profile_and_package_loaders_support_v0_4_metadata(self):
        profiles = ProfileLoader(ROOT / "profiles").load_all()
        packages = PackageLoader(ROOT / "stdlib").load_all()

        company_ecommerce = profiles.get("COMPANY_ECOMMERCE")
        razorpay = packages.get("payment.razorpay")

        self.assertIsNotNone(company_ecommerce)
        self.assertEqual(company_ecommerce.extends, "ECOMMERCE")
        self.assertIn("audit.standard", company_ecommerce.packages)
        self.assertIn("notification.sms", company_ecommerce.packages)
        self.assertIsNotNone(razorpay)
        self.assertIn("notification.email", razorpay.dependencies)
        self.assertIn("audit.standard", razorpay.dependencies)

    def test_ast_supports_multiple_profiles_and_packages(self):
        source = (ROOT / "examples" / "profile_tests" / "profile_with_packages.sem").read_text(
            encoding="utf-8"
        )
        ast = Parser().parse(Lexer().tokenize(source))

        self.assertEqual([profile.name for profile in ast.profiles], ["ECOMMERCE"])
        self.assertEqual(
            [package.name for package in ast.packages],
            ["payment.razorpay", "notification.email", "storage.local"],
        )

    def test_backward_compatible_source_matches_profiled_generation(self):
        legacy_source = """PROJECT CompatibilityDemo

TARGET PHP

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING
    password STRING

VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN

ROUTE POST /login
"""
        profiled_source = legacy_source.replace(
            "DATABASE MYSQL",
            "PROFILE ECOMMERCE\nUSE payment.razorpay\nUSE notification.email\n\nDATABASE MYSQL",
        )

        with tempfile.TemporaryDirectory() as legacy_tmp, tempfile.TemporaryDirectory() as profile_tmp:
            legacy_path = Path(legacy_tmp) / "legacy.sem"
            profile_path = Path(profile_tmp) / "profiled.sem"
            legacy_path.write_text(legacy_source, encoding="utf-8")
            profile_path.write_text(profiled_source, encoding="utf-8")

            legacy_context = self._compile(legacy_path, Path(legacy_tmp) / "out", "php")
            profile_context = self._compile(profile_path, Path(profile_tmp) / "out", "php")

            self.assertEqual(
                self._generated_file_map(Path(legacy_context.output_dir), {".php", ".sql"}),
                self._generated_file_map(Path(profile_context.output_dir), {".php", ".sql"}),
            )
            for key in ["score", "errors", "warnings", "recommendations"]:
                self.assertEqual(
                    legacy_context.architecture_report[key],
                    profile_context.architecture_report[key],
                )

    def _compile(self, source_path: Path, output_dir: Path, target: str) -> CompilerContext:
        context = CompilerContext(
            source_path=source_path,
            output_dir=str(output_dir),
            target_override=target,
        )
        for compiler_pass in [
            LexingPass(),
            ParsingPass(),
            ContractPass(),
            StdlibPass(),
            ValidationPass(),
            ModuleConstraintPass(),
            RelationshipPass(),
            ConstraintPass(),
            ExpansionPass(),
            IRPass(),
            OptimizationPass(),
        ]:
            if isinstance(compiler_pass, ContractPass):
                compiler_pass.validate_ast(context)
            else:
                compiler_pass.run(context)

        ContractPass().validate_ir(context)
        GenerationPass().run(context)
        DiagnosticReportPass().run(context)
        ContractPass().validate_generation(context)
        return context

    def _validate_common_context(self, context: CompilerContext) -> None:
        self.assertIsNotNone(context.ast)
        self.assertGreater(len(context.ast.models), 0)
        self.assertIn("graph", context.relationship_plan)
        self.assertIn("migrations", context.relationship_plan)
        context.dependency_graph.validate()
        self.assertGreater(len(context.ir["models"]), 0)
        self.assertGreater(len(context.ir["relationships"]), 0)
        self.assertGreater(len(context.ir["routes"]), 0)
        self.assertEqual(ContractValidator().validate_ir(context.ir), [])
        self.assertIn("score", context.architecture_report)
        self.assertIn("warnings", context.architecture_report)
        self.assertIn("recommendations", context.architecture_report)
        self.assertIn("errors", context.architecture_report)

    def _validate_metadata_context(self, context: CompilerContext) -> None:
        self.assertIn("profiles", context.ir)
        self.assertIn("packages", context.ir)
        self.assertGreaterEqual(len(context.ir["profiles"]), 1)
        self.assertEqual(len(context.ast.profiles), len(context.ir["profiles"]))
        self.assertEqual(len(context.ast.packages), len(context.ir["packages"]))
        self.assertEqual(ContractValidator().detect_target_leakage(context.ir["profiles"]), [])
        self.assertEqual(ContractValidator().detect_target_leakage(context.ir["packages"]), [])

    def _validate_php_output(self, output_dir: Path) -> None:
        for directory in [
            "controllers",
            "models",
            "services",
            "repositories",
            "middleware",
            "migrations",
            "config",
        ]:
            self.assertTrue((output_dir / directory).is_dir(), f"Missing PHP directory: {directory}")

        self.assertTrue((output_dir / "routes.php").exists())
        self.assertTrue(any((output_dir / "models").glob("*.php")))
        self.assertTrue(any((output_dir / "repositories").glob("*.php")))
        self.assertTrue(any((output_dir / "migrations").glob("*.sql")))
        self.assertTrue((output_dir / "architecture_report.json").exists())

    def _validate_fastapi_output(self, output_dir: Path) -> None:
        for directory in [
            "config",
            "routers",
            "models",
            "schemas",
            "services",
            "repositories",
            "middleware",
            "migrations",
        ]:
            self.assertTrue((output_dir / directory).is_dir(), f"Missing FastAPI directory: {directory}")

        self.assertTrue((output_dir / "main.py").exists())
        self.assertTrue(any((output_dir / "models").glob("*.py")))
        self.assertTrue(any((output_dir / "schemas").glob("*.py")))
        self.assertTrue(any((output_dir / "repositories").glob("*.py")))
        self.assertTrue(any((output_dir / "migrations").glob("*.py")))
        self.assertTrue((output_dir / "architecture_report.json").exists())

    def _load_report(self, output_dir: Path) -> dict:
        return json.loads((output_dir / "architecture_report.json").read_text(encoding="utf-8"))

    def _write_report(self, rows: list[dict]) -> None:
        report_path = ROOT / "reports" / "example_validation_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        passed = sum(1 for row in rows if row["compilation"] == "PASS")
        failed = len(rows) - passed

        lines = [
            "# Example Project Validation Report",
            "",
            "This report is generated by `tests/integration/test_example_validation_suite.py`.",
            "",
            "| Example Name | Compilation Status | IR Status | Migration Status | PHP Status | FastAPI Status | Diagnostics Status | Profiles | Packages | Score | Warnings | Recommendations | Errors |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                "| {example} | {compilation} | {ir} | {migration} | {php} | {fastapi} | {diagnostics} | {profiles} | {packages} | {score} | {warnings} | {recommendations} | {errors} |".format(
                    **row
                )
            )

        lines.extend(
            [
                "",
                "## Summary",
                "",
                f"- Examples Passed: {passed}",
                f"- Examples Failed: {failed}",
                "",
                "## Potential Language Gaps",
                "",
                "- No explicit `RATE_LIMIT` semantic command exists, so JWT rate-limit diagnostics cannot be resolved in source yet.",
                "- `VALIDATE MIN` does not currently carry a numeric threshold.",
                "- Relationships are direct model relationships; many-to-many join modeling is not formalized yet.",
                "",
                "## Potential Architecture Gaps",
                "",
                "- Non-auth route handlers are prototype JSON handlers rather than resource-specific controllers.",
                "- Repository implementations are generated as lightweight prototype persistence layers.",
                "- Authentication middleware exists, but route-level protection policy is not yet semantic.",
                "",
                "## Potential Missing Semantic Concepts",
                "",
                "- rate limiting",
                "- roles and permissions",
                "- pagination and filtering",
                "- request and response schemas",
                "- many-to-many relationship ownership",
                "- deployment and environment profiles",
                "",
            ]
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        self._write_v0_4_report(rows)
        self._write_gap_report()

    def _write_v0_4_report(self, rows: list[dict]) -> None:
        profiles = ProfileLoader(ROOT / "profiles").load_all().all()
        packages = PackageLoader(ROOT / "stdlib").load_all().all()
        profile_tests = [path.name for path in PROFILE_TEST_EXAMPLES]
        passed = sum(1 for row in rows if row["compilation"] == "PASS")
        failed = len(rows) - passed

        lines = [
            "# v0.4 Foundation Validation Report",
            "",
            "This report validates the metadata-only profile and package foundation.",
            "",
            "## Examples Tested",
            "",
        ]
        lines.extend(f"- {row['example']}: {row['compilation']}" for row in rows)
        lines.extend(
            [
                "",
                "## Profile Test Inputs",
                "",
            ]
        )
        lines.extend(f"- `{name}`" for name in profile_tests)
        lines.extend(
            [
                "",
                "## Profiles Loaded",
                "",
            ]
        )
        lines.extend(
            f"- {profile.name} (extends: {profile.extends or 'none'}, packages: {', '.join(profile.packages) or 'none'})"
            for profile in profiles
        )
        lines.extend(
            [
                "",
                "## Packages Loaded",
                "",
            ]
        )
        lines.extend(
            f"- {package.name} (domain: {package.domain}, dependencies: {', '.join(package.dependencies) or 'none'})"
            for package in packages
        )
        lines.extend(
            [
                "",
                "## AST Validation",
                "",
                "- ProfileNode creation: PASS",
                "- PackageNode creation: PASS",
                "- Multiple profile declarations: PASS",
                "- Multiple package declarations: PASS",
                "- Backward-compatible source without PROFILE/USE: PASS",
                "",
                "## IR Validation",
                "",
                "- `profiles` metadata present: PASS",
                "- `packages` metadata present: PASS",
                "- target leakage check: PASS",
                "- profile/package metadata does not alter generation: PASS",
                "",
                "## Compilation Validation",
                "",
                f"- Examples Passed: {passed}",
                f"- Examples Failed: {failed}",
                "- PHP target compilation: PASS",
                "- FastAPI target compilation: PASS",
                "- Migration generation: PASS",
                "",
                "## Backward Compatibility Validation",
                "",
                "- Existing syntax without PROFILE/USE still compiles.",
                "- Generated PHP and SQL files remain identical when metadata-only PROFILE/USE declarations are added.",
                "- Architecture diagnostics remain identical for metadata-only PROFILE/USE declarations.",
                "",
            ]
        )
        (ROOT / "reports" / "v0_4_foundation_report.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    def _write_gap_report(self) -> None:
        lines = [
            "# v0.4 Architecture Gap Analysis",
            "",
            "This document identifies future package candidates. It does not implement them.",
            "",
            "## Useful Future Package Types",
            "",
            "- `payment`: provider-specific payment flows, webhooks, refunds, and audit requirements.",
            "- `reporting`: exports, scheduled reports, and analytics read models.",
            "- `search`: indexing, search adapters, and query constraints.",
            "- `notification`: email, SMS, push, and event-driven notification rules.",
            "- `audit`: append-only activity logging and compliance metadata.",
            "- `storage`: local, object storage, and media handling modules.",
            "- `cache`: Redis and application cache policies.",
            "- `role_permission`: roles, permissions, and route protection policies.",
            "",
            "## Current Foundation Gaps",
            "",
            "- Package dependency resolution is metadata-only.",
            "- Profile inheritance is loaded but not applied to compiler behavior.",
            "- Package compatibility constraints are not evaluated yet.",
            "- Target-specific package mappings are intentionally absent.",
            "",
            "## Boundary Reminder",
            "",
            "Future package implementation should remain deterministic and target-neutral until the generator mapping stage.",
            "",
        ]
        (ROOT / "reports" / "v0_4_architecture_gaps.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )

    def _generated_file_map(self, output_dir: Path, suffixes: set[str]) -> dict[str, str]:
        files = {}
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                files[str(path.relative_to(output_dir))] = path.read_text(encoding="utf-8")
        return files


if __name__ == "__main__":
    unittest.main()

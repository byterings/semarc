import json
import tempfile
import unittest
from pathlib import Path

from compiler.context import CompilerContext
from compiler.contracts import ContractValidator
from compiler.passes.constraint_pass import ConstraintPass
from compiler.passes.contract_pass import ContractPass
from compiler.passes.diagnostic_report_pass import DiagnosticReportPass
from compiler.passes.expansion_pass import ExpansionPass
from compiler.passes.generation_pass import GenerationPass
from compiler.passes.ir_pass import IRPass
from compiler.passes.lexing_pass import LexingPass
from compiler.passes.optimization_pass import OptimizationPass
from compiler.passes.parsing_pass import ParsingPass
from compiler.passes.relationship_pass import RelationshipPass
from compiler.passes.validation_pass import ValidationPass


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = [
    ("Blog API", ROOT / "examples" / "blog_api.sem"),
    ("ECommerce", ROOT / "examples" / "ecommerce.sem"),
    ("CRM", ROOT / "examples" / "crm.sem"),
    ("Inventory", ROOT / "examples" / "inventory.sem"),
    ("School Management", ROOT / "examples" / "school_management.sem"),
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
                self._validate_php_output(Path(tmpdir) / "php")
                self._validate_fastapi_output(Path(tmpdir) / "fastapi")

                report = self._load_report(Path(tmpdir) / "fastapi")
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
            ValidationPass(),
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
            "| Example Name | Compilation Status | IR Status | Migration Status | PHP Status | FastAPI Status | Diagnostics Status | Score | Warnings | Recommendations | Errors |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                "| {example} | {compilation} | {ir} | {migration} | {php} | {fastapi} | {diagnostics} | {score} | {warnings} | {recommendations} | {errors} |".format(
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


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path

from architecture.relationship_engine import RelationshipEngine
from architecture.dependency_graph import DependencyGraph, DependencyGraphError
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
from lexer.lexer import Lexer
from parser.parser import Parser


BLOG_SOURCE = """PROJECT BlogAPI

TARGET FASTAPI

DATABASE MYSQL

AUTH JWT

MODEL User
    name STRING
    email STRING

MODEL Post
    title STRING
    content STRING

RELATION User HAS_MANY Post

ROUTE POST /login
ROUTE GET /posts
"""


class SemarcRelationshipTests(unittest.TestCase):
    def test_relationship_parsing(self):
        tokens = Lexer().tokenize(BLOG_SOURCE)
        ast = Parser().parse(tokens)

        self.assertEqual(len(ast.relations), 1)
        relation = ast.relations[0]
        self.assertEqual(relation.source_model, "User")
        self.assertEqual(relation.relation_type, "HAS_MANY")
        self.assertEqual(relation.target_model, "Post")

    def test_migration_plan_contains_foreign_key(self):
        ast = Parser().parse(Lexer().tokenize(BLOG_SOURCE))
        plan = RelationshipEngine().build(ast)

        self.assertEqual(plan["foreign_keys"][0]["table"], "posts")
        self.assertEqual(plan["foreign_keys"][0]["column"], "user_id")
        self.assertEqual(plan["foreign_keys"][0]["references_table"], "users")

    def test_compiler_passes_and_fastapi_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "blog.sem"
            output_dir = Path(tmpdir) / "out"
            source_path.write_text(BLOG_SOURCE, encoding="utf-8")

            context = CompilerContext(
                source_path=source_path,
                output_dir=str(output_dir),
                target_override="fastapi",
            )
            for compiler_pass in [
                LexingPass(),
                ParsingPass(),
                ValidationPass(),
                RelationshipPass(),
                ConstraintPass(),
                ExpansionPass(),
                IRPass(),
                OptimizationPass(),
                GenerationPass(),
            ]:
                compiler_pass.run(context)

            self.assertIn("RelationshipPass", context.compiler_passes)
            self.assertIn("ConstraintPass", context.compiler_passes)
            self.assertTrue((output_dir / "migrations" / "create_posts_table.py").exists())
            self.assertTrue((output_dir / "models" / "post.py").exists())
            self.assertIn("foreign_keys", context.ir)

    def test_deterministic_migration_generation(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_output = self._compile_to(first)
            second_output = self._compile_to(second)

            first_migration = (first_output / "migrations" / "create_posts_table.py").read_text(
                encoding="utf-8"
            )
            second_migration = (second_output / "migrations" / "create_posts_table.py").read_text(
                encoding="utf-8"
            )

            self.assertEqual(first_migration, second_migration)

    def test_ir_contract_has_no_target_leakage(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)
        errors = ContractValidator().validate_ir(context.ir)

        self.assertEqual(errors, [])

    def test_dependency_graph_detects_duplicate_dependency(self):
        graph = DependencyGraph()
        graph.add_dependency("AuthMiddleware", "TokenService")
        graph.add_dependency("AuthMiddleware", "TokenService")

        with self.assertRaises(DependencyGraphError):
            graph.validate()

    def test_same_semantic_input_supports_independent_targets(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            fastapi_context = self._compile_context(first, target="fastapi", generate=True)
            php_context = self._compile_context(second, target="php", generate=True)

            self.assertEqual(fastapi_context.target_profile["generator"], "fastapi")
            self.assertEqual(php_context.target_profile["generator"], "php")
            self.assertTrue((Path(first) / "out" / "main.py").exists())
            self.assertTrue((Path(second) / "out" / "routes.php").exists())

    def test_auth_constraint_warns_about_rate_limiting(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)
        warning_codes = [warning["code"] for warning in context.architecture_report["warnings"]]

        self.assertIn("AUTH001", warning_codes)

    def test_conflicting_auth_strategies_generate_diagnostic_error(self):
        source = """PROJECT AuthConflict

DATABASE MYSQL

AUTH JWT
AUTH SESSION

MODEL User
    email STRING

ROUTE POST /login
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)
        error_codes = [error["code"] for error in context.architecture_report["errors"]]

        self.assertIn("AUTH002", error_codes)

    def test_route_constraint_recommends_login_validation(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)
        recommendation_codes = [
            recommendation["code"]
            for recommendation in context.architecture_report["recommendations"]
        ]

        self.assertIn("ROUTE001", recommendation_codes)

    def test_database_constraint_warns_when_database_is_missing(self):
        source = """PROJECT MissingDatabase

AUTH JWT

MODEL User
    email STRING

ROUTE POST /login
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)
        warning_codes = [warning["code"] for warning in context.architecture_report["warnings"]]

        self.assertIn("DB001", warning_codes)

    def test_relationship_constraint_adds_relationship_recommendation(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)
        recommendation_codes = [
            recommendation["code"]
            for recommendation in context.architecture_report["recommendations"]
        ]

        self.assertIn("REL002", recommendation_codes)

    def test_architecture_score_is_deterministic(self):
        first = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)
        second = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)

        self.assertEqual(first.architecture_report["score"], second.architecture_report["score"])

    def test_diagnostic_report_file_is_generated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._compile_context(tmpdir, target="fastapi", generate=True)
            report_path = Path(tmpdir) / "out" / "architecture_report.json"

            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("score", report)
            self.assertIn("warnings", report)

    def test_pass_order_is_explicit(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)

        self.assertEqual(
            context.compiler_passes,
            [
                "LexingPass",
                "ParsingPass",
                "ContractPass:AST",
                "ValidationPass",
                "RelationshipPass",
                "ConstraintPass",
                "ExpansionPass",
                "IRPass",
                "OptimizationPass",
                "ContractPass:IR",
            ],
        )

    def _compile_to(self, tmpdir: str) -> Path:
        context = self._compile_context(tmpdir, target="fastapi", generate=True)
        return Path(tmpdir) / "out"

    def _compile_context(self, tmpdir: str, target: str, generate: bool) -> CompilerContext:
        return self._compile_context_with_source(tmpdir, BLOG_SOURCE, target, generate)

    def _compile_context_with_source(
        self,
        tmpdir: str,
        source: str,
        target: str,
        generate: bool,
    ) -> CompilerContext:
        source_path = Path(tmpdir) / "blog.sem"
        output_dir = Path(tmpdir) / "out"
        source_path.write_text(source, encoding="utf-8")
        context = CompilerContext(source_path=source_path, output_dir=str(output_dir), target_override=target)
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

        if generate:
            GenerationPass().run(context)
            DiagnosticReportPass().run(context)
            ContractPass().validate_generation(context)

        return context


if __name__ == "__main__":
    unittest.main()

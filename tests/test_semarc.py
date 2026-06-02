import json
import os
import tempfile
import unittest
from pathlib import Path

from architecture.packages import PackageLoader
from architecture.relationship_engine import RelationshipEngine
from architecture.profiles import ProfileLoader
from architecture.stdlib import (
    DuplicateModuleError,
    ModuleDefinition,
    ModuleDependencyError,
    ModuleDependencyResolver,
    ModuleRegistry,
    StdlibLoader,
    StdlibLoadingError,
)
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
from compiler.passes.stdlib_pass import StdlibPass
from compiler.passes.validation_pass import ValidationPass
from lexer.lexer import Lexer
from parser.parser import Parser
from validator.validator import SemanticValidationError


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

    def test_profile_and_package_hooks_parse_as_metadata(self):
        source = """PROJECT ProfileDemo

PROFILE Ecommerce
USE payment.razorpay

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))

        self.assertEqual(ast.profiles[0].name, "Ecommerce")
        self.assertEqual(ast.packages[0].name, "payment.razorpay")

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
                StdlibPass(),
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

    def test_profile_and_package_metadata_reaches_ir_without_generation_effect(self):
        source = """PROJECT ProfileDemo

TARGET PHP

PROFILE Ecommerce
USE payment.razorpay

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING
    password STRING

VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN

ROUTE POST /login
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="php", generate=False)

        self.assertEqual(context.ir["profiles"], [{"name": "Ecommerce", "metadata": {}}])
        self.assertEqual(context.ir["packages"], [{"name": "payment.razorpay", "metadata": {}}])
        self.assertEqual(ContractValidator().validate_ir(context.ir), [])

    def test_profile_and_package_metadata_does_not_change_generated_php(self):
        base_source = """PROJECT ProfileDemo

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
        profiled_source = base_source.replace(
            "DATABASE MYSQL",
            "PROFILE Ecommerce\nUSE payment.razorpay\n\nDATABASE MYSQL",
        )

        with tempfile.TemporaryDirectory() as base_tmp, tempfile.TemporaryDirectory() as profile_tmp:
            base_context = self._compile_context_with_source(base_tmp, base_source, target="php", generate=True)
            profile_context = self._compile_context_with_source(profile_tmp, profiled_source, target="php", generate=True)

            self.assertEqual(
                self._generated_file_map(Path(base_context.output_dir), suffixes={".php", ".sql"}),
                self._generated_file_map(Path(profile_context.output_dir), suffixes={".php", ".sql"}),
            )

    def test_profile_metadata_loads_safely(self):
        registry = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all()
        ecommerce = registry.get("Ecommerce")

        self.assertIsNotNone(ecommerce)
        self.assertIn("payment", ecommerce.packages)

    def test_package_metadata_loads_safely(self):
        registry = PackageLoader(Path(__file__).resolve().parents[1] / "stdlib").load_all()
        payment = registry.get("payment")

        self.assertIsNotNone(payment)
        self.assertEqual(payment.domain, "payment")
        self.assertIn("notification", payment.dependencies)

    def test_stdlib_discovers_modules_recursively(self):
        modules = StdlibLoader(Path(__file__).resolve().parents[1] / "stdlib").load_all()
        module_names = {module.name for module in modules}

        self.assertIn("auth.jwt", module_names)
        self.assertIn("cache.redis", module_names)
        self.assertIn("payment.razorpay", module_names)

    def test_module_registry_detects_duplicate_module_names(self):
        registry = ModuleRegistry()
        module = ModuleDefinition("auth.jwt", "1.0", "JWT", Path("stdlib/auth/jwt/module.yaml"))

        registry.register(module)
        with self.assertRaises(DuplicateModuleError):
            registry.register(module)

    def test_invalid_module_definition_raises_diagnostic_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "stdlib" / "broken" / "module.yaml"
            module_path.parent.mkdir(parents=True)
            module_path.write_text("name: broken.module\nversion: 1.0\n", encoding="utf-8")

            with self.assertRaises(StdlibLoadingError) as error:
                StdlibLoader(Path(tmpdir) / "stdlib").load_all()

            self.assertIn("SEM5003", str(error.exception))

    def test_invalid_module_dependency_schema_raises_sem6003(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "stdlib" / "broken" / "module.yaml"
            module_path.parent.mkdir(parents=True)
            module_path.write_text(
                "name: broken.module\nversion: 1.0\ndescription: broken\ndepends: auth.jwt\n",
                encoding="utf-8",
            )

            with self.assertRaises(StdlibLoadingError) as error:
                StdlibLoader(Path(tmpdir) / "stdlib").load_all()

            self.assertIn("SEM6003", str(error.exception))

    def test_module_dependency_resolver_resolves_recursive_dependencies(self):
        registry = ModuleRegistry()
        payment = ModuleDefinition(
            "payment.razorpay",
            "1.0",
            "payment",
            Path("payment/module.yaml"),
            ["notification.email"],
        )
        notification = ModuleDefinition(
            "notification.email",
            "1.0",
            "email",
            Path("notification/module.yaml"),
            ["audit.standard"],
        )
        audit = ModuleDefinition("audit.standard", "1.0", "audit", Path("audit/module.yaml"))
        for module in [payment, notification, audit]:
            registry.register(module)

        resolved = ModuleDependencyResolver(registry).resolve([payment])

        self.assertEqual(
            [module.name for module in resolved],
            ["payment.razorpay", "notification.email", "audit.standard"],
        )

    def test_module_dependency_resolver_eliminates_duplicate_dependencies(self):
        registry = ModuleRegistry()
        first = ModuleDefinition("first.module", "1.0", "first", Path("first"), ["shared.module"])
        second = ModuleDefinition("second.module", "1.0", "second", Path("second"), ["shared.module"])
        shared = ModuleDefinition("shared.module", "1.0", "shared", Path("shared"))
        for module in [first, second, shared]:
            registry.register(module)

        resolved = ModuleDependencyResolver(registry).resolve([first, second])

        self.assertEqual(
            [module.name for module in resolved],
            ["first.module", "shared.module", "second.module"],
        )

    def test_module_dependency_resolver_detects_circular_dependencies(self):
        registry = ModuleRegistry()
        auth = ModuleDefinition("auth.jwt", "1.0", "auth", Path("auth"), ["audit.standard"])
        audit = ModuleDefinition("audit.standard", "1.0", "audit", Path("audit"), ["auth.jwt"])
        registry.register(auth)
        registry.register(audit)

        with self.assertRaises(ModuleDependencyError) as error:
            ModuleDependencyResolver(registry).resolve([auth])

        self.assertIn("SEM6001", str(error.exception))
        self.assertIn("auth.jwt", str(error.exception))
        self.assertIn("audit.standard", str(error.exception))

    def test_module_dependency_resolver_detects_missing_dependency(self):
        registry = ModuleRegistry()
        payment = ModuleDefinition(
            "payment.razorpay",
            "1.0",
            "payment",
            Path("payment"),
            ["notification.sms"],
        )
        registry.register(payment)

        with self.assertRaises(ModuleDependencyError) as error:
            ModuleDependencyResolver(registry).resolve([payment])

        self.assertIn("SEM6002 Missing module dependency: notification.sms", str(error.exception))

    def test_module_dependency_resolver_handles_large_dependency_chain(self):
        registry = ModuleRegistry()
        modules = []
        for index in range(30):
            dependency = [f"chain.module{index + 1}"] if index < 29 else []
            module = ModuleDefinition(
                f"chain.module{index}",
                "1.0",
                "chain",
                Path(f"chain{index}"),
                dependency,
            )
            modules.append(module)
            registry.register(module)

        resolved = ModuleDependencyResolver(registry).resolve([modules[0]])

        self.assertEqual(len(resolved), 30)
        self.assertEqual(resolved[0].name, "chain.module0")
        self.assertEqual(resolved[-1].name, "chain.module29")

    def test_use_validation_resolves_known_modules(self):
        source = """PROJECT ModuleDemo

TARGET FASTAPI

USE auth.jwt
USE cache.redis

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        resolved = [module.name for module in context.resolved_modules]
        report_modules = [module["name"] for module in context.architecture_report["modules"]]

        self.assertEqual(resolved, ["auth.jwt", "cache.redis"])
        self.assertEqual(report_modules, ["auth.jwt", "cache.redis"])

    def test_use_validation_resolves_module_dependencies_into_report(self):
        source = """PROJECT PaymentDemo

TARGET FASTAPI

USE payment.razorpay

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        resolved = [module.name for module in context.resolved_modules]
        dependency_modules = [module.name for module in context.dependency_resolved_modules]

        self.assertEqual(resolved, ["payment.razorpay", "notification.email", "audit.standard"])
        self.assertEqual(dependency_modules, ["notification.email", "audit.standard"])
        self.assertEqual(
            context.architecture_report["resolved_through_dependencies"],
            ["notification.email", "audit.standard"],
        )

    def test_unknown_use_remains_legacy_metadata(self):
        source = """PROJECT UnknownModuleDemo

USE auth.missing
USE company.internal_standard

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertEqual(context.resolved_modules, [])
        self.assertEqual(
            [package["name"] for package in context.ir["packages"]],
            ["auth.missing", "company.internal_standard"],
        )

    def test_duplicate_known_use_triggers_sem5002(self):
        source = """PROJECT DuplicateUseDemo

USE auth.jwt
USE auth.jwt

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertIn("SEM5002 Duplicate module usage: auth.jwt", str(error.exception))

    def test_stdlib_resolution_is_independent_of_current_working_directory(self):
        source = """PROJECT CwdIndependent

USE auth.jwt
USE cache.redis

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as source_tmp, tempfile.TemporaryDirectory() as cwd_tmp:
            source_path = Path(source_tmp) / "cwd_independent.sem"
            source_path.write_text(source, encoding="utf-8")
            context = CompilerContext(source_path=source_path)
            try:
                os.chdir(cwd_tmp)
                for compiler_pass in [
                    LexingPass(),
                    ParsingPass(),
                    StdlibPass(),
                    ValidationPass(),
                ]:
                    compiler_pass.run(context)
            finally:
                os.chdir(original_cwd)

        self.assertEqual([module.name for module in context.resolved_modules], ["auth.jwt", "cache.redis"])

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
                "StdlibPass",
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
            StdlibPass(),
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

    def _generated_file_map(self, output_dir: Path, suffixes: set[str]) -> dict[str, str]:
        files = {}
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                files[str(path.relative_to(output_dir))] = path.read_text(encoding="utf-8")
        return files


if __name__ == "__main__":
    unittest.main()

import json
import os
import tempfile
import unittest
from pathlib import Path

from architecture.analysis import ArchitectureAnalyzer
from architecture.packages import PackageLoader
from architecture.profiles import Profile, ProfileCompositionError, ProfileCompositionResolver
from architecture.relationship_engine import RelationshipEngine
from architecture.profiles import ProfileLoader, ProfileLoadingError, ProfileRegistry
from architecture.stdlib import (
    DuplicateModuleError,
    ModuleDefinition,
    ModuleConstraintError,
    ModuleConstraintValidator,
    ModuleDependencyError,
    ModuleDependencyResolver,
    ModuleRegistry,
    StdlibLoader,
    StdlibLoadingError,
)
from architecture.dependency_graph import DependencyGraph, DependencyGraphError
from compiler.context import CompilerContext
from compiler.contracts import ContractValidator
from compiler.passes.architecture_analysis_pass import ArchitectureAnalysisPass
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
from compiler.passes.profile_pass import ProfilePass
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
                ArchitectureAnalysisPass(),
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

    def test_nestjs_target_selection(self):
        source = """PROJECT NestTarget

TARGET NESTJS

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target=None, generate=False)

        self.assertEqual(context.target_profile["generator"], "nestjs")
        self.assertEqual(context.target_profile["framework"], "nestjs")

    def test_nestjs_project_generation(self):
        context = self._compile_context_with_source(
            tempfile.mkdtemp(),
            self._nestjs_source(),
            target="nestjs",
            generate=True,
        )
        output_dir = Path(context.output_dir)

        self.assertTrue((output_dir / "src" / "app.module.ts").exists())
        self.assertTrue((output_dir / "src" / "modules" / "users" / "users.module.ts").exists())

    def test_nestjs_model_service_and_controller_generation(self):
        context = self._compile_context_with_source(
            tempfile.mkdtemp(),
            self._nestjs_source(),
            target="nestjs",
            generate=True,
        )
        users_dir = Path(context.output_dir) / "src" / "modules" / "users"

        model = (users_dir / "user.model.ts").read_text(encoding="utf-8")
        service = (users_dir / "users.service.ts").read_text(encoding="utf-8")
        controller = (users_dir / "users.controller.ts").read_text(encoding="utf-8")

        self.assertIn("export class User", model)
        self.assertIn("email!: string;", model)
        self.assertIn("@Injectable()", service)
        self.assertIn("export class UserService", service)
        self.assertIn("@Controller('users')", controller)
        self.assertIn("@Get()", controller)
        self.assertIn("export class UserController", controller)

    def test_nestjs_auth_scaffold_generation(self):
        context = self._compile_context_with_source(
            tempfile.mkdtemp(),
            self._nestjs_source(auth=True),
            target="nestjs",
            generate=True,
        )
        output_dir = Path(context.output_dir)
        app_module = (output_dir / "src" / "app.module.ts").read_text(encoding="utf-8")
        guard = (output_dir / "src" / "guards" / "auth.guard.ts").read_text(encoding="utf-8")

        self.assertTrue((output_dir / "src" / "modules" / "auth" / "auth.module.ts").exists())
        self.assertIn("AuthModule", app_module)
        self.assertIn("export class AuthGuard implements CanActivate", guard)

    def test_nestjs_app_module_registers_generated_modules(self):
        context = self._compile_context_with_source(
            tempfile.mkdtemp(),
            self._nestjs_source(auth=True),
            target="nestjs",
            generate=True,
        )
        app_module = (Path(context.output_dir) / "src" / "app.module.ts").read_text(encoding="utf-8")

        self.assertIn("import { UserModule } from './modules/users/users.module';", app_module)
        self.assertIn("UserModule", app_module)
        self.assertIn("AuthModule", app_module)

    def test_nestjs_generates_multiple_model_modules(self):
        source = """PROJECT MultiNest

TARGET NESTJS

DATABASE MYSQL

MODEL User
    email STRING

MODEL Product
    name STRING

ROUTE GET /users
ROUTE GET /products
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="nestjs", generate=True)
        output_dir = Path(context.output_dir)

        self.assertTrue((output_dir / "src" / "modules" / "users" / "users.module.ts").exists())
        self.assertTrue((output_dir / "src" / "modules" / "products" / "products.module.ts").exists())

    def test_nestjs_generation_supports_profile_based_projects(self):
        source = """PROJECT ProfileNest

PROFILE BLOG

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="nestjs", generate=True)

        self.assertEqual(context.target_profile["generator"], "nestjs")
        self.assertTrue((Path(context.output_dir) / "src" / "modules" / "users" / "users.service.ts").exists())
        self.assertIn("auth.jwt", [module.name for module in context.resolved_modules])

    def test_nestjs_generation_supports_dependency_based_projects(self):
        source = """PROJECT DependencyNest

USE payment.razorpay

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="nestjs", generate=True)

        self.assertEqual(
            [module.name for module in context.resolved_modules],
            ["payment.razorpay", "notification.email", "audit.standard"],
        )
        self.assertTrue((Path(context.output_dir) / "src" / "app.module.ts").exists())

    def test_nestjs_target_does_not_break_php_or_fastapi_generation(self):
        with tempfile.TemporaryDirectory() as php_tmp, tempfile.TemporaryDirectory() as fastapi_tmp:
            php_context = self._compile_context_with_source(php_tmp, self._nestjs_source(), target="php", generate=True)
            fastapi_context = self._compile_context_with_source(
                fastapi_tmp,
                self._nestjs_source(),
                target="fastapi",
                generate=True,
            )

            self.assertTrue((Path(php_context.output_dir) / "routes.php").exists())
            self.assertTrue((Path(fastapi_context.output_dir) / "main.py").exists())

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
        self.assertIn("auth.jwt", ecommerce.modules)

    def test_invalid_profile_modules_schema_raises_sem8003(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "profiles" / "broken.profile"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text(
                "name: Broken\nmodules: auth.jwt\n",
                encoding="utf-8",
            )

            with self.assertRaises(ProfileLoadingError) as error:
                ProfileLoader(Path(tmpdir) / "profiles").load_all()

            self.assertIn("SEM8003", str(error.exception))

    def test_profile_composition_resolves_simple_modules(self):
        registry = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all()
        profiles, modules = ProfileCompositionResolver(registry).resolve(["ECOMMERCE"])

        self.assertEqual([profile.name for profile in profiles], ["Ecommerce"])
        self.assertEqual(modules, ["auth.jwt", "payment.razorpay", "cache.redis"])

    def test_profile_composition_resolves_inherited_modules(self):
        registry = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all()
        profiles, modules = ProfileCompositionResolver(registry).resolve(["COMPANY_ECOMMERCE"])

        self.assertEqual(
            [profile.name for profile in profiles],
            ["Ecommerce", "COMPANY_ECOMMERCE"],
        )
        self.assertEqual(
            modules,
            ["auth.jwt", "payment.razorpay", "cache.redis", "audit.standard", "notification.sms"],
        )

    def test_profile_composition_eliminates_duplicate_modules(self):
        registry = ProfileRegistry()
        registry.register(ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all().get("Ecommerce"))
        registry.register(ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all().get("CompanyStandard"))
        registry.register(
            ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load(
                Path(__file__).resolve().parents[1] / "profiles" / "company_ecommerce.profile"
            )
        )
        _, modules = ProfileCompositionResolver(registry).resolve(["ECOMMERCE", "COMPANY_STANDARD"])

        self.assertEqual(modules, ["auth.jwt", "payment.razorpay", "cache.redis"])

    def test_profile_composition_detects_unknown_profile(self):
        registry = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load_all()

        with self.assertRaises(ProfileCompositionError) as error:
            ProfileCompositionResolver(registry).resolve(["UNKNOWN_PROFILE"])

        self.assertIn("SEM8001", str(error.exception))

    def test_profile_composition_detects_circular_inheritance(self):
        registry = ProfileRegistry()
        circular_a = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load(
            Path(__file__).resolve().parents[1] / "profiles" / "blog.profile"
        )
        circular_b = ProfileLoader(Path(__file__).resolve().parents[1] / "profiles").load(
            Path(__file__).resolve().parents[1] / "profiles" / "crm.profile"
        )
        circular_a = type(circular_a)(
            name="A",
            description="A",
            extends=["B"],
            modules=["auth.jwt"],
            packages=[],
            metadata={},
        )
        circular_b = type(circular_b)(
            name="B",
            description="B",
            extends=["A"],
            modules=["notification.email"],
            packages=[],
            metadata={},
        )
        registry.register(circular_a)
        registry.register(circular_b)

        with self.assertRaises(ProfileCompositionError) as error:
            ProfileCompositionResolver(registry).resolve(["A"])

        self.assertIn("SEM8002", str(error.exception))

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

    def test_invalid_module_requires_schema_raises_sem7003(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "stdlib" / "broken" / "module.yaml"
            module_path.parent.mkdir(parents=True)
            module_path.write_text(
                "name: broken.module\nversion: 1.0\ndescription: broken\nrequires: database.mysql\n",
                encoding="utf-8",
            )

            with self.assertRaises(StdlibLoadingError) as error:
                StdlibLoader(Path(tmpdir) / "stdlib").load_all()

            self.assertIn("SEM7003", str(error.exception))

    def test_invalid_module_conflicts_schema_raises_sem7003(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            module_path = Path(tmpdir) / "stdlib" / "broken" / "module.yaml"
            module_path.parent.mkdir(parents=True)
            module_path.write_text(
                "name: broken.module\nversion: 1.0\ndescription: broken\nconflicts: auth.jwt\n",
                encoding="utf-8",
            )

            with self.assertRaises(StdlibLoadingError) as error:
                StdlibLoader(Path(tmpdir) / "stdlib").load_all()

            self.assertIn("SEM7003", str(error.exception))

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

    def test_module_constraint_validator_accepts_satisfied_database_requirement(self):
        module = ModuleDefinition(
            "payment.razorpay",
            "1.0",
            "payment",
            Path("payment"),
            requirements=["database.mysql"],
        )
        source = """PROJECT RequirementOk

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))
        ModuleConstraintValidator().validate(ast, [module])

    def test_module_constraint_validator_rejects_unsatisfied_database_requirement(self):
        module = ModuleDefinition(
            "payment.razorpay",
            "1.0",
            "payment",
            Path("payment"),
            requirements=["database.mysql"],
        )
        source = """PROJECT RequirementFail

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source.replace("MYSQL", "SQLITE")))
        with self.assertRaises(ModuleConstraintError) as error:
            ModuleConstraintValidator().validate(ast, [module])

        self.assertIn("SEM7001", str(error.exception))

    def test_module_constraint_validator_accepts_target_requirement(self):
        module = ModuleDefinition(
            "cache.redis",
            "1.0",
            "cache",
            Path("cache"),
            requirements=["target.fastapi"],
        )
        source = """PROJECT TargetOk

TARGET FASTAPI

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))
        ModuleConstraintValidator().validate(ast, [module])

    def test_module_constraint_validator_accepts_module_requirement(self):
        auth = ModuleDefinition("auth.jwt", "1.0", "auth", Path("auth"))
        payment = ModuleDefinition(
            "payment.razorpay",
            "1.0",
            "payment",
            Path("payment"),
            requirements=["auth.jwt"],
        )
        source = """PROJECT ModuleReqOk

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))
        ModuleConstraintValidator().validate(ast, [auth, payment])

    def test_module_constraint_validator_detects_conflict(self):
        auth_jwt = ModuleDefinition(
            "auth.jwt",
            "1.0",
            "auth",
            Path("auth"),
            conflicts=["auth.session"],
        )
        auth_session = ModuleDefinition("auth.session", "1.0", "session", Path("session"))
        source = """PROJECT ConflictDemo

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))
        with self.assertRaises(ModuleConstraintError) as error:
            ModuleConstraintValidator().validate(ast, [auth_jwt, auth_session])

        self.assertIn("SEM7002", str(error.exception))


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

    def test_profile_composition_resolves_modules_without_explicit_use(self):
        source = """PROJECT ProfileModuleDemo

TARGET FASTAPI

PROFILE ECOMMERCE

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)

        self.assertEqual(
            [module.name for module in context.resolved_modules],
            ["auth.jwt", "payment.razorpay", "notification.email", "audit.standard", "cache.redis"],
        )
        self.assertEqual(
            context.architecture_report["modules_from_profiles"],
            ["auth.jwt", "payment.razorpay", "cache.redis"],
        )

    def test_architecture_analyzer_warns_about_public_route_without_authentication(self):
        source = """PROJECT PublicApi

DATABASE MYSQL

MODEL Post
    title STRING

ROUTE GET /posts
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        warning_codes = [
            warning["code"]
            for warning in context.architecture_report["architecture_analysis"]["warnings"]
        ]

        self.assertIn("SEM9001", warning_codes)

    def test_architecture_analyzer_recommends_payment_audit_pairing(self):
        ast = Parser().parse(Lexer().tokenize(BLOG_SOURCE.replace("AUTH JWT", "")))
        modules = [ModuleDefinition("payment.demo", "1.0", "payment", Path("payment"))]
        report = ArchitectureAnalyzer().analyze(ast=ast, resolved_modules=modules).to_dict()
        recommendation_codes = [item["code"] for item in report["recommendations"]]

        self.assertIn("SEM9002", recommendation_codes)

    def test_architecture_analyzer_warns_about_unused_model(self):
        source = """PROJECT UnusedModel

DATABASE MYSQL

MODEL User
    email STRING

MODEL Comment
    body STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        warnings = context.architecture_report["architecture_analysis"]["warnings"]

        self.assertIn("SEM9003", [warning["code"] for warning in warnings])
        self.assertIn("Comment", [warning["message"] for warning in warnings][0] + "".join(
            warning["message"] for warning in warnings
        ))

    def test_architecture_analyzer_recommends_against_ecommerce_sqlite(self):
        source = """PROJECT Shop

DATABASE SQLITE

MODEL User
    email STRING

ROUTE GET /users
"""
        profiles = [Profile(name="Ecommerce", modules=[])]
        report = ArchitectureAnalyzer().analyze(
            ast=Parser().parse(Lexer().tokenize(source)),
            loaded_profiles=profiles,
        ).to_dict()
        recommendation_codes = [item["code"] for item in report["recommendations"]]

        self.assertIn("SEM9004", recommendation_codes)

    def test_architecture_analyzer_recommends_when_auth_has_no_protected_routes(self):
        source = """PROJECT AuthOnly

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING

ROUTE POST /login
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        recommendation_codes = [
            item["code"]
            for item in context.architecture_report["architecture_analysis"]["recommendations"]
        ]

        self.assertIn("SEM9005", recommendation_codes)

    def test_architecture_analyzer_supports_multiple_findings(self):
        source = """PROJECT MultiFindings

DATABASE MYSQL

MODEL User
    email STRING

MODEL Report
    title STRING

ROUTE GET /users
ROUTE GET /reports
"""
        report = self._compile_context_with_source(
            tempfile.mkdtemp(),
            source,
            target="fastapi",
            generate=True,
        ).architecture_report["architecture_analysis"]
        warning_codes = [item["code"] for item in report["warnings"]]

        self.assertIn("SEM9001", warning_codes)
        self.assertNotIn("SEM9003", warning_codes)

    def test_architecture_analyzer_avoids_false_positives(self):
        source = """PROJECT NoFalsePositives

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING

MODEL Post
    title STRING

RELATION User HAS_MANY Post

ROUTE POST /login
ROUTE GET /posts
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        report = context.architecture_report["architecture_analysis"]

        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["recommendations"], [])

    def test_unknown_profile_raises_sem8001(self):
        source = """PROJECT UnknownProfileDemo

PROFILE UNKNOWN_PROFILE

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertIn("SEM8001 Unknown profile: UNKNOWN_PROFILE", str(error.exception))

    def test_profile_constraint_interaction_raises_sem7001(self):
        source = """PROJECT ProfileConstraintFail

PROFILE ECOMMERCE

DATABASE SQLITE

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertIn("SEM7001 Module requirement not satisfied", str(error.exception))

    def test_multiple_profiles_compose_deterministically(self):
        source = """PROJECT MultiProfileDemo

PROFILE BLOG
PROFILE COMPANY_STANDARD

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)

        self.assertEqual(context.architecture_report["profiles"], ["Blog", "CompanyStandard"])
        self.assertEqual(context.architecture_report["modules_from_profiles"], ["auth.jwt"])

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

    def test_payment_module_database_requirement_is_satisfied(self):
        source = """PROJECT PaymentOk

TARGET FASTAPI

USE payment.razorpay

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)

        self.assertIn("database.mysql", context.architecture_report["requirements"])

    def test_payment_module_database_requirement_violation_raises_sem7001(self):
        source = """PROJECT PaymentFail

TARGET FASTAPI

USE payment.razorpay

DATABASE SQLITE

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertIn("SEM7001 Module requirement not satisfied", str(error.exception))

    def test_auth_module_conflict_raises_sem7002(self):
        source = """PROJECT AuthConflict

USE auth.jwt
USE auth.session

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=False)

        self.assertIn("SEM7002 Module conflict detected", str(error.exception))

    def test_architecture_report_includes_requirements_and_conflicts(self):
        source = """PROJECT ReportDemo

TARGET FASTAPI

USE auth.jwt
USE payment.razorpay

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)

        self.assertIn("requirements", context.architecture_report)
        self.assertIn("database.mysql", context.architecture_report["requirements"])
        self.assertIn("conflicts", context.architecture_report)
        self.assertIn("auth.session", context.architecture_report["conflicts"])

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

    def test_architecture_report_includes_analysis_section(self):
        source = """PROJECT ReportAnalysis

DATABASE MYSQL

MODEL Post
    title STRING

ROUTE GET /posts
"""
        context = self._compile_context_with_source(tempfile.mkdtemp(), source, target="fastapi", generate=True)
        report = context.architecture_report

        self.assertIn("architecture_analysis", report)
        self.assertIn("warnings", report["architecture_analysis"])
        self.assertIn("recommendations", report["architecture_analysis"])

    def test_pass_order_is_explicit(self):
        context = self._compile_context(tempfile.mkdtemp(), target="fastapi", generate=False)

        self.assertEqual(
            context.compiler_passes,
            [
                "LexingPass",
                "ParsingPass",
                "ContractPass:AST",
                "ProfilePass",
                "StdlibPass",
                "ValidationPass",
                "ModuleConstraintPass",
                "RelationshipPass",
                "ConstraintPass",
                "ArchitectureAnalysisPass",
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
        target: str | None,
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
            ProfilePass(),
            StdlibPass(),
            ValidationPass(),
            ModuleConstraintPass(),
            RelationshipPass(),
            ConstraintPass(),
            ArchitectureAnalysisPass(),
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

    def _nestjs_source(self, auth: bool = False) -> str:
        auth_block = "\nAUTH JWT\n" if auth else ""
        return f"""PROJECT NestShop

TARGET NESTJS

DATABASE MYSQL
{auth_block}
MODEL User
    email STRING
    name STRING

ROUTE GET /users
ROUTE POST /users
"""

    def _generated_file_map(self, output_dir: Path, suffixes: set[str]) -> dict[str, str]:
        files = {}
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.suffix in suffixes:
                files[str(path.relative_to(output_dir))] = path.read_text(encoding="utf-8")
        return files


if __name__ == "__main__":
    unittest.main()

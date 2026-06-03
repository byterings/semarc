import tempfile
import unittest
from pathlib import Path

from architecture.profiles import Profile, ProfileCompositionError, ProfileCompositionResolver, ProfileRegistry
from architecture.stdlib import (
    ModuleConstraintError,
    ModuleConstraintValidator,
    ModuleDefinition,
    ModuleDependencyError,
    ModuleDependencyResolver,
    ModuleRegistry,
)
from lexer.lexer import Lexer
from parser.parser import Parser
from tests.support import compile_source
from validator.validator import SemanticValidationError


class RegressionTestCase(unittest.TestCase):
    def compile(self, source: str, target: str = "fastapi", generate: bool = False):
        with tempfile.TemporaryDirectory() as tmpdir:
            return compile_source(source, tmpdir, target, generate=generate)


class FixedBugRegressionTests(RegressionTestCase):
    def test_duplicate_known_module_usage_stays_blocked(self):
        source = """PROJECT DuplicateModule

USE auth.jwt
USE auth.jwt

DATABASE MYSQL

MODEL User
    email STRING

ROUTE GET /users
"""
        with self.assertRaises(SemanticValidationError) as error:
            self.compile(source)

        self.assertIn("SEM5002 Duplicate module usage: auth.jwt", str(error.exception))

    def test_circular_module_dependency_stays_blocked(self):
        registry = ModuleRegistry()
        first = ModuleDefinition("first.module", "1.0", "first", Path("first"), ["second.module"])
        second = ModuleDefinition("second.module", "1.0", "second", Path("second"), ["first.module"])
        registry.register(first)
        registry.register(second)

        with self.assertRaises(ModuleDependencyError) as error:
            ModuleDependencyResolver(registry).resolve([first])

        self.assertIn("SEM6001", str(error.exception))

    def test_circular_profile_inheritance_stays_blocked(self):
        registry = ProfileRegistry()
        registry.register(Profile(name="A", extends=["B"], modules=[]))
        registry.register(Profile(name="B", extends=["A"], modules=[]))

        with self.assertRaises(ProfileCompositionError) as error:
            ProfileCompositionResolver(registry).resolve(["A"])

        self.assertIn("SEM8002", str(error.exception))

    def test_invalid_module_constraint_stays_blocked(self):
        module = ModuleDefinition(
            "payment.demo",
            "1.0",
            "payment",
            Path("payment"),
            requirements=["database.mysql"],
        )
        source = """PROJECT InvalidConstraint

DATABASE SQLITE

MODEL User
    email STRING

ROUTE GET /users
"""
        ast = Parser().parse(Lexer().tokenize(source))

        with self.assertRaises(ModuleConstraintError) as error:
            ModuleConstraintValidator().validate(ast, [module])

        self.assertIn("SEM7001", str(error.exception))

    def test_profile_inheritance_chain_remains_deterministic(self):
        registry = ProfileRegistry()
        registry.register(Profile(name="Base", modules=["auth.jwt"]))
        registry.register(Profile(name="Saas", extends=["Base"], modules=["notification.email"]))
        registry.register(Profile(name="Commerce", extends=["Saas"], modules=["payment.razorpay"]))

        profiles, modules = ProfileCompositionResolver(registry).resolve(["Commerce"])

        self.assertEqual([profile.name for profile in profiles], ["Base", "Saas", "Commerce"])
        self.assertEqual(modules, ["auth.jwt", "notification.email", "payment.razorpay"])

    def test_architecture_analysis_warning_regression(self):
        source = """PROJECT PublicRoute

DATABASE MYSQL

MODEL Post
    title STRING

ROUTE GET /posts
"""
        context = self.compile(source, target="fastapi", generate=True)
        warning_codes = [
            warning["code"]
            for warning in context.architecture_report["architecture_analysis"]["warnings"]
        ]

        self.assertIn("SEM9001", warning_codes)

import tempfile
import unittest

from semarc.lexer.lexer import Lexer
from semarc.parser.parser import Parser, ParserError
from tests.support import compile_source
from semarc.validator.validator import SemanticValidationError, SemanticValidator


BASE = """PROJECT Demo

DATABASE SQLITE

AUTH JWT

MODEL User
    name STRING
    email STRING UNIQUE
    password STRING
    bio TEXT OPTIONAL

MODEL Post
    title STRING
    body TEXT
    published BOOLEAN OPTIONAL

RELATION User HAS_MANY Post
"""


def parse(source: str):
    return Parser().parse(Lexer().tokenize(source))


def validate(source: str) -> None:
    SemanticValidator().validate(parse(source))


class FieldModifierTests(unittest.TestCase):
    def test_field_modifiers_are_parsed(self):
        ast = parse(BASE)
        user = ast.models[0]
        modifiers = {field.name: field.modifiers for field in user.fields}

        self.assertEqual(modifiers["email"], ["UNIQUE"])
        self.assertEqual(modifiers["bio"], ["OPTIONAL"])
        self.assertEqual(modifiers["name"], [])

    def test_date_types_are_parsed(self):
        ast = parse("PROJECT Demo\nMODEL Event\n    starts_on DATE\n    begins_at DATETIME OPTIONAL\n")
        self.assertEqual([(field.name, field.field_type) for field in ast.models[0].fields], [("starts_on", "DATE"), ("begins_at", "DATETIME")])

    def test_min_and_max_are_rejected_on_date_fields(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate("PROJECT Demo\nMODEL Event\n    starts_on DATE\nVALIDATE starts_on MIN 1\n")
        self.assertIn("MIN validation requires a text or numeric field", str(raised.exception))

    def test_unknown_field_modifier_is_rejected(self):
        with self.assertRaises(ParserError):
            parse("PROJECT Demo\nMODEL User\n    email STRING PRIMARY\n")

    def test_field_named_like_a_keyword_is_allowed(self):
        ast = parse("PROJECT Demo\nMODEL Ticket\n    service STRING\n    status STRING\n")
        self.assertEqual([field.name for field in ast.models[0].fields], ["service", "status"])

    def test_model_named_like_a_keyword_is_allowed(self):
        ast = parse("PROJECT Demo\nMODEL Profile\n    bio TEXT\nMODEL Route\n    name STRING\n")
        self.assertEqual([model.name for model in ast.models], ["Profile", "Route"])

    def test_implicit_columns_cannot_be_declared(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate("PROJECT Demo\nMODEL Post\n    id INTEGER\n")
        self.assertIn("generated automatically", str(raised.exception))

    def test_duplicate_fields_are_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate("PROJECT Demo\nMODEL Post\n    title STRING\n    title TEXT\n")
        self.assertIn("Duplicate field: Post.title", str(raised.exception))

    def test_naming_rules_are_enforced(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate("PROJECT Demo\nMODEL post\n    Title STRING\n")
        message = str(raised.exception)
        self.assertIn("Model name must be PascalCase: post", message)
        self.assertIn("Field name must be snake_case: post.Title", message)

    def test_declared_foreign_key_column_conflicts_with_relation(self):
        source = BASE.replace("    title STRING\n", "    title STRING\n    user_id INTEGER\n")
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source)
        self.assertIn("Post.user_id conflicts with the foreign key", str(raised.exception))


class RouteSyntaxTests(unittest.TestCase):
    def test_path_parameters_and_access_are_parsed(self):
        ast = parse(BASE + "ROUTE GET /posts/{id} PUBLIC\nROUTE DELETE /posts/{id} PROTECTED\nROUTE GET /posts\n")
        routes = [(route.method, route.path, route.access) for route in ast.routes]

        self.assertEqual(
            routes,
            [
                ("GET", "/posts/{id}", "PUBLIC"),
                ("DELETE", "/posts/{id}", "PROTECTED"),
                ("GET", "/posts", None),
            ],
        )

    def test_invalid_access_modifier_is_rejected(self):
        with self.assertRaises(ParserError):
            parse(BASE + "ROUTE GET /posts PRIVATE\n")

    def test_invalid_path_segment_is_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "ROUTE GET /posts/{Id}\n")
        self.assertIn("Invalid route path segment '{Id}'", str(raised.exception))

    def test_duplicate_path_parameters_are_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "ROUTE GET /posts/{id}/comments/{id}\n")
        self.assertIn("Duplicate route parameter", str(raised.exception))

    def test_reserved_experience_routes_cannot_be_declared(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "ROUTE GET /health\n")
        self.assertIn("reserved", str(raised.exception))

    def test_protected_route_requires_auth(self):
        source = BASE.replace("AUTH JWT\n", "") + "ROUTE GET /posts PROTECTED\n"
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source)
        self.assertIn("PROTECTED but no AUTH strategy", str(raised.exception))

    def test_register_route_requires_jwt(self):
        source = BASE.replace("AUTH JWT\n", "") + "ROUTE POST /register\n"
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source)
        self.assertIn("POST /register requires AUTH JWT", str(raised.exception))

    def test_reserved_commands_have_explicit_error(self):
        for command in ["SERVICE Mailer", "CONFIG cache"]:
            with self.subTest(command=command), self.assertRaises(ParserError) as raised:
                parse(f"PROJECT Demo\n{command}\n")
            self.assertIn("reserved for a future SEMARC version", str(raised.exception))


class ValidationRuleTests(unittest.TestCase):
    def test_min_and_max_take_numeric_parameters(self):
        ast = parse(BASE + "VALIDATE password REQUIRED MIN 8 MAX 64\n")
        validation = ast.validations[0]

        self.assertEqual(validation.rules, ["REQUIRED", "MIN", "MAX"])
        self.assertEqual(validation.parameters, {"MIN": 8, "MAX": 64})
        self.assertIsNone(validation.model_name)

    def test_legacy_min_without_value_defaults_to_six(self):
        ast = parse(BASE + "VALIDATE password REQUIRED MIN\n")
        self.assertEqual(ast.validations[0].parameters, {"MIN": 6})

    def test_max_requires_value(self):
        with self.assertRaises(ParserError):
            parse(BASE + "VALIDATE title MAX\n")

    def test_model_scoped_validation(self):
        ast = parse(BASE + "VALIDATE Post.title REQUIRED MAX 120\n")
        validation = ast.validations[0]

        self.assertEqual(validation.model_name, "Post")
        self.assertEqual(validation.field_name, "title")
        validate(BASE + "VALIDATE Post.title REQUIRED MAX 120\n")

    def test_validation_for_unknown_field_is_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE Post.subtitle REQUIRED\n")
        self.assertIn("Undefined field in validation: Post.subtitle", str(raised.exception))

    def test_unscoped_validation_must_match_a_field(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE phone REQUIRED\n")
        self.assertIn("not declared on any model: phone", str(raised.exception))

    def test_auth_credentials_can_be_validated_without_user_model(self):
        source = "PROJECT Demo\nAUTH JWT\nMODEL Lead\n    name STRING\nVALIDATE password REQUIRED MIN 8\n"
        validate(source)

    def test_email_rule_requires_text_field(self):
        source = BASE.replace("    published BOOLEAN OPTIONAL\n", "    published BOOLEAN OPTIONAL\n    views INTEGER\n")
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source + "VALIDATE views EMAIL\n")
        self.assertIn("EMAIL validation requires a STRING or TEXT field", str(raised.exception))

    def test_string_max_cannot_exceed_column_size(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE title MAX 500\n")
        self.assertIn("MAX 500 exceeds the STRING limit of 255", str(raised.exception))
        validate(BASE + "VALIDATE body MAX 5000\n")

    def test_password_max_cannot_exceed_bcrypt_limit(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE password MAX 100\n")
        self.assertIn("72 character password limit", str(raised.exception))

    def test_min_greater_than_max_is_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE title MIN 10 MAX 5\n")
        self.assertIn("MIN 10 is greater than MAX 5", str(raised.exception))

    def test_required_conflicts_with_optional(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE bio REQUIRED\n")
        self.assertIn("REQUIRED validation conflicts with OPTIONAL field", str(raised.exception))

    def test_duplicate_validation_is_rejected(self):
        with self.assertRaises(SemanticValidationError) as raised:
            validate(BASE + "VALIDATE title REQUIRED\nVALIDATE title MAX 50\n")
        self.assertIn("Duplicate validation for title", str(raised.exception))


class AuthRuleTests(unittest.TestCase):
    def test_session_auth_alone_is_rejected(self):
        source = BASE.replace("AUTH JWT", "AUTH SESSION")
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source)
        self.assertIn("AUTH SESSION is not implemented", str(raised.exception))

    def test_credential_fields_must_be_required_strings(self):
        source = BASE.replace("    password STRING\n", "    password INTEGER\n")
        with self.assertRaises(SemanticValidationError) as raised:
            validate(source)
        self.assertIn("User.password to be a required STRING field", str(raised.exception))

    def test_user_without_password_is_completed_by_auth(self):
        validate("PROJECT Demo\nAUTH JWT\nMODEL User\n    email STRING\n")


class ExampleCompatibilityTests(unittest.TestCase):
    def test_full_syntax_compiles_through_ir(self):
        source = BASE + "\n".join(
            [
                "VALIDATE email REQUIRED EMAIL",
                "VALIDATE password REQUIRED MIN 8",
                "VALIDATE Post.title REQUIRED MAX 120",
                "ROUTE GET /posts",
                "ROUTE GET /posts/{id}",
                "ROUTE POST /posts",
                "ROUTE PATCH /posts/{id}",
                "ROUTE DELETE /posts/{id}",
                "ROUTE GET /users/{id} PROTECTED",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "php", generate=False)
        self.assertEqual(len(context.ast.routes), 6)


if __name__ == "__main__":
    unittest.main()

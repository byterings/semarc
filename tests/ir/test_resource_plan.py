import tempfile
import unittest

from semarc.compiler.contracts import ContractValidator
from tests.support import compile_source


BLOG = """PROJECT Blog

DATABASE SQLITE

AUTH JWT

MODEL User
    name STRING
    email STRING

MODEL Post
    title STRING
    body TEXT OPTIONAL

MODEL Tag
    label STRING UNIQUE

RELATION User HAS_MANY Post

VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN 8
VALIDATE Post.title REQUIRED MAX 120

ROUTE GET /posts
ROUTE POST /posts
ROUTE GET /posts/{id}
ROUTE PUT /posts/{id}
ROUTE PATCH /posts/{id}
ROUTE DELETE /posts/{id} PUBLIC
ROUTE GET /users/{id}/posts
ROUTE GET /posts/{id}/archive
ROUTE GET /stats
ROUTE POST /tags PUBLIC
"""


def compile_ir(source: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        return compile_source(source, tmpdir, "php", generate=False).ir


def route(ir: dict, method: str, path: str) -> dict:
    return next(item for item in ir["routes"] if item["method"] == method and item["path"] == path)


def model(ir: dict, name: str) -> dict:
    return next(item for item in ir["models"] if item["name"] == name)


def field(model_ir: dict, name: str) -> dict:
    return next(item for item in model_ir["fields"] if item["name"] == name)


class RouteOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ir = compile_ir(BLOG)

    def test_collection_and_item_operations(self):
        expected = {
            ("GET", "/posts"): {"kind": "list", "model": "Post"},
            ("POST", "/posts"): {"kind": "create", "model": "Post"},
            ("GET", "/posts/{id}"): {"kind": "read", "model": "Post", "parameter": "id"},
            ("PUT", "/posts/{id}"): {"kind": "replace", "model": "Post", "parameter": "id", "owner_only": True},
            ("PATCH", "/posts/{id}"): {"kind": "update", "model": "Post", "parameter": "id", "owner_only": True},
            ("DELETE", "/posts/{id}"): {"kind": "delete", "model": "Post", "parameter": "id"},
        }
        for (method, path), operation in expected.items():
            with self.subTest(route=f"{method} {path}"):
                self.assertEqual(route(self.ir, method, path)["operation"], operation)

    def test_nested_relationship_route(self):
        self.assertEqual(
            route(self.ir, "GET", "/users/{id}/posts")["operation"],
            {
                "kind": "list_related",
                "model": "Post",
                "parent_model": "User",
                "parameter": "id",
                "foreign_key": "user_id",
            },
        )

    def test_unresolved_routes_are_custom(self):
        self.assertEqual(route(self.ir, "GET", "/posts/{id}/archive")["operation"], {"kind": "custom", "model": "Post"})
        self.assertEqual(route(self.ir, "GET", "/stats")["operation"], {"kind": "custom", "model": None})
        self.assertEqual(route(self.ir, "GET", "/stats")["handler"], {"type": "todo", "action": "custom"})

    def test_session_routes_and_refresh_token_table(self):
        self.assertEqual(route(self.ir, "POST", "/token/refresh")["access"], "public")
        self.assertEqual(route(self.ir, "POST", "/logout")["operation"]["kind"], "auth_logout")
        self.assertEqual(route(self.ir, "POST", "/me/password")["access"], "protected")
        table = next(item for item in self.ir["migrations"]["tables"] if item["table"] == "refresh_tokens")
        self.assertTrue(table["internal"])
        self.assertEqual(table["foreign_keys"][0]["on_delete"], "CASCADE")
        names = [item["table"] for item in self.ir["migrations"]["tables"]]
        self.assertLess(names.index("users"), names.index("refresh_tokens"))

    def test_auth_routes_are_added(self):
        for method, path, kind in [("POST", "/register", "auth_register"), ("POST", "/login", "auth_login"), ("GET", "/me", "auth_me")]:
            with self.subTest(path=path):
                entry = route(self.ir, method, path)
                self.assertEqual(entry["operation"]["kind"], kind)
                self.assertEqual(entry["origin"], "auth")
                self.assertEqual(entry["handler"]["component"], "AuthController")

    def test_list_route_is_completed_for_every_declared_model(self):
        self.assertEqual(route(self.ir, "GET", "/tags")["origin"], "completed")
        self.assertEqual(route(self.ir, "GET", "/users")["origin"], "completed")
        self.assertEqual(route(self.ir, "GET", "/posts")["origin"], "declared")

    def test_path_parameters_are_listed(self):
        self.assertEqual(route(self.ir, "GET", "/users/{id}/posts")["parameters"], ["id"])
        self.assertEqual(route(self.ir, "GET", "/posts")["parameters"], [])


class AccessPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ir = compile_ir(BLOG)

    def test_reads_are_public_and_writes_are_protected_by_default(self):
        self.assertEqual(route(self.ir, "GET", "/posts")["access"], "public")
        self.assertEqual(route(self.ir, "POST", "/posts")["access"], "protected")
        self.assertEqual(route(self.ir, "PATCH", "/posts/{id}")["access"], "protected")

    def test_explicit_access_overrides_default(self):
        self.assertEqual(route(self.ir, "DELETE", "/posts/{id}")["access"], "public")
        self.assertEqual(route(self.ir, "POST", "/tags")["access"], "public")

    def test_auth_model_routes_are_protected(self):
        self.assertEqual(route(self.ir, "GET", "/users")["access"], "protected")

    def test_auth_endpoints_access(self):
        self.assertEqual(route(self.ir, "POST", "/register")["access"], "public")
        self.assertEqual(route(self.ir, "POST", "/login")["access"], "public")
        self.assertEqual(route(self.ir, "GET", "/me")["access"], "protected")

    def test_protected_writes_on_owned_models_are_owner_only(self):
        self.assertTrue(route(self.ir, "PATCH", "/posts/{id}")["operation"]["owner_only"])
        self.assertNotIn("owner_only", route(self.ir, "DELETE", "/posts/{id}")["operation"])
        self.assertNotIn("owner_only", route(self.ir, "POST", "/posts")["operation"])

    def test_models_without_owner_are_not_owner_only(self):
        ir = compile_ir(BLOG + "ROUTE PATCH /tags/{id}\n")
        self.assertNotIn("owner_only", route(ir, "PATCH", "/tags/{id}")["operation"])

    def test_everything_is_public_without_auth(self):
        ir = compile_ir(BLOG.replace("AUTH JWT\n", "").replace(" PUBLIC", "").replace("VALIDATE password REQUIRED MIN 8\n", ""))
        self.assertEqual({item["access"] for item in ir["routes"]}, {"public"})
        self.assertIsNone(ir["auth"])


class ModelSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ir = compile_ir(BLOG)

    def test_auth_identity_and_secret_are_completed(self):
        user = model(self.ir, "User")
        self.assertTrue(field(user, "email")["unique"])
        self.assertTrue(field(user, "password")["secret"])
        self.assertEqual(self.ir["auth"]["model"], "User")
        self.assertFalse(self.ir["auth"]["implicit_model"])

    def test_field_flags(self):
        post = model(self.ir, "Post")
        self.assertTrue(field(post, "title")["required"])
        self.assertFalse(field(post, "body")["required"])
        self.assertTrue(field(model(self.ir, "Tag"), "label")["unique"])

    def test_validation_rules_are_merged_into_fields(self):
        user = model(self.ir, "User")
        self.assertEqual(
            field(user, "email")["rules"],
            {"required": True, "not_empty": True, "email": True, "min": None, "max": None, "in": None},
        )
        self.assertEqual(field(user, "password")["rules"]["min"], 8)
        self.assertEqual(field(model(self.ir, "Post"), "title")["rules"]["max"], 120)
        self.assertIsNone(field(model(self.ir, "Tag"), "label")["rules"]["max"])

    def test_references_and_dependents(self):
        post = model(self.ir, "Post")
        user = model(self.ir, "User")
        self.assertEqual(
            post["references"],
            [{"column": "user_id", "model": "User", "table": "users", "unique": False, "owner": True}],
        )
        self.assertEqual(user["dependents"], [{"model": "Post", "table": "posts", "column": "user_id"}])

    def test_list_query_fields_exclude_secrets_and_datetimes(self):
        user = model(self.ir, "User")
        post = model(self.ir, "Post")
        self.assertNotIn("password", user["query"]["filters"])
        self.assertNotIn("password", user["query"]["sort"])
        self.assertEqual(post["query"]["filters"], {"id": "INTEGER", "title": "STRING", "body": "TEXT", "user_id": "INTEGER"})
        self.assertEqual(post["query"]["sort"], ["id", "title", "body", "user_id", "created_at", "updated_at"])

        ir = compile_ir("PROJECT P\n\nMODEL Event\n    starts_at DATETIME\n    day DATE\n")
        event = model(ir, "Event")
        self.assertNotIn("starts_at", event["query"]["filters"])
        self.assertEqual(event["query"]["filters"]["day"], "DATE")
        self.assertIn("starts_at", event["query"]["sort"])

    def test_table_and_resource_names(self):
        self.assertEqual(model(self.ir, "Post")["table"], "posts")
        self.assertEqual(model(self.ir, "Post")["resource"], "posts")

    def test_implicit_auth_model_when_user_is_not_declared(self):
        ir = compile_ir("PROJECT Crm\n\nDATABASE SQLITE\n\nAUTH JWT\n\nMODEL Lead\n    name STRING\n\nROUTE GET /leads\n")
        user = model(ir, "User")

        self.assertEqual(user["origin"], "auth")
        self.assertEqual([item["name"] for item in user["fields"]], ["email", "password"])
        self.assertTrue(ir["auth"]["implicit_model"])
        self.assertNotIn(("GET", "/users"), {(item["method"], item["path"]) for item in ir["routes"]})
        self.assertIn("users", [table["table"] for table in ir["migrations"]["tables"]])

    def test_has_one_foreign_key_is_unique(self):
        ir = compile_ir("PROJECT P\n\nMODEL User\n    name STRING\n\nMODEL Profile\n    bio TEXT\n\nRELATION User HAS_ONE Profile\n")
        self.assertTrue(model(ir, "Profile")["references"][0]["unique"])

    def test_inverse_relations_share_one_foreign_key(self):
        ir = compile_ir(BLOG.replace("RELATION User HAS_MANY Post\n", "RELATION User HAS_MANY Post\nRELATION Post BELONGS_TO User\n"))
        self.assertEqual([item["column"] for item in model(ir, "Post")["foreign_keys"]], ["user_id"])


class IrPurityTests(unittest.TestCase):
    def test_extended_ir_has_no_target_leakage(self):
        ir = compile_ir(BLOG)
        self.assertEqual(ContractValidator().validate_ir(ir), [])


if __name__ == "__main__":
    unittest.main()

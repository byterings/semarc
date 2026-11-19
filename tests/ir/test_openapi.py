import tempfile
import unittest

from semarc.generator.utils.openapi import OpenApiBuilder
from tests.ir.test_resource_plan import BLOG
from tests.support import compile_source


def build(source: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        ir = compile_source(source, tmpdir, "php", generate=False).ir
    return OpenApiBuilder().build(ir)


class OpenApiDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = build(BLOG)

    def test_document_describes_every_route(self):
        paths = self.document["paths"]
        for path in ["/", "/health", "/routes", "/posts", "/posts/{id}", "/users/{id}/posts", "/register", "/login", "/me"]:
            self.assertIn(path, paths)
        self.assertEqual(self.document["openapi"], "3.1.0")
        self.assertEqual(self.document["info"]["title"], "Blog")

    def test_protected_and_owner_only_operations(self):
        patch = self.document["paths"]["/posts/{id}"]["patch"]
        self.assertEqual(patch["security"], [{"bearerAuth": []}])
        self.assertIn("403", patch["responses"])
        self.assertIn("401", patch["responses"])
        self.assertNotIn("security", self.document["paths"]["/posts"]["get"])

    def test_schemas_follow_field_rules(self):
        schemas = self.document["components"]["schemas"]
        self.assertEqual(schemas["PostCreate"]["properties"]["title"]["maxLength"], 120)
        self.assertEqual(schemas["PostCreate"]["required"], ["title"])
        self.assertNotIn("password", schemas["User"]["properties"])
        self.assertEqual(schemas["UserCreate"]["properties"]["password"]["format"], "password")
        self.assertEqual(schemas["Post"]["properties"]["body"]["type"], ["string", "null"])

    def test_list_operations_document_filters_and_sorting(self):
        names = [parameter["name"] for parameter in self.document["paths"]["/posts"]["get"]["parameters"]]
        self.assertEqual(names[:3], ["limit", "offset", "sort"])
        self.assertIn("title", names)
        self.assertIn("user_id", names)

    def test_auth_operations_document_rate_limit(self):
        self.assertIn("429", self.document["paths"]["/login"]["post"]["responses"])

    def test_custom_routes_document_not_implemented(self):
        self.assertIn("501", self.document["paths"]["/stats"]["get"]["responses"])

    def test_document_is_valid_openapi(self):
        try:
            from openapi_spec_validator import validate
        except ImportError:
            self.skipTest("openapi-spec-validator is not installed")
        validate(self.document)


if __name__ == "__main__":
    unittest.main()

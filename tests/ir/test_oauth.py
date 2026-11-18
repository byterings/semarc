import tempfile
import unittest
from pathlib import Path

from semarc.generator.utils.api_scenario import ApiScenarioBuilder
from semarc.generator.utils.openapi import OpenApiBuilder
from semarc.generator.utils.project_runtime import docker_compose, env_values
from semarc.validator.validator import SemanticValidationError
from tests.support import ROOT, compile_file, compile_source

OAUTH = """PROJECT Demo
DATABASE SQLITE
AUTH JWT
USE auth.oauth.google
"""


def plan(source: str) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        return compile_source(source, tmpdir, "php", generate=False).ir


class OAuthPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmpdir:
            cls.ir = compile_file(ROOT / "tests" / "fixtures" / "edge_oauth.sem", Path(tmpdir) / "out", "php", generate=False).ir
        cls.routes = {(route["method"], route["path"]): route for route in cls.ir["routes"]}

    def test_feature_lists_providers_in_order(self):
        oauth = self.ir["auth"]["features"]["oauth"]
        self.assertEqual([provider["name"] for provider in oauth["providers"]], ["github", "google"])
        self.assertEqual((oauth["table"], oauth["state_ttl_seconds"], oauth["name_field"]), ("oauth_accounts", 600, "name"))
        google = oauth["providers"][1]
        self.assertEqual(google["env_prefix"], "OAUTH_GOOGLE")
        self.assertEqual(google["token_url"], "https://oauth2.googleapis.com/token")
        self.assertIsNone(google["emails_url"])

    def test_routes_are_public(self):
        for provider in ["github", "google"]:
            start = self.routes[("GET", f"/oauth/{provider}")]
            callback = self.routes[("POST", f"/oauth/{provider}/callback")]
            self.assertEqual(start["operation"], {"kind": "auth_oauth_start", "model": "User", "provider": provider})
            self.assertEqual(callback["operation"]["kind"], "auth_oauth_callback")
            self.assertEqual((start["access"], callback["access"]), ("public", "public"))

    def test_accounts_table_cascades(self):
        table = next(item for item in self.ir["migrations"]["tables"] if item["table"] == "oauth_accounts")
        self.assertTrue(table["internal"])
        self.assertEqual([item["name"] for item in table["fields"]], ["provider", "provider_subject"])
        self.assertEqual(table["foreign_keys"][0]["on_delete"], "CASCADE")

    def test_runtime_settings(self):
        env = env_values(self.ir)
        for name in ["OAUTH_GOOGLE_CLIENT_ID", "OAUTH_GOOGLE_CLIENT_SECRET", "OAUTH_GOOGLE_REDIRECT_URI", "OAUTH_GITHUB_CLIENT_ID"]:
            self.assertEqual(env[name], "")
        self.assertIn("OAUTH_GITHUB_ENDPOINT: ${OAUTH_GITHUB_ENDPOINT:-}", docker_compose(self.ir, 8000))

    def test_openapi(self):
        document = OpenApiBuilder().build(self.ir)
        callback = document["paths"]["/oauth/google/callback"]["post"]
        self.assertEqual(set(callback["responses"]), {"200", "400", "422", "429", "502", "503"})
        self.assertIn("OAuthCallback", document["components"]["schemas"])

    def test_scenario(self):
        scenario = ApiScenarioBuilder().build(self.ir)
        self.assertEqual(scenario["env"]["OAUTH_GOOGLE_CLIENT_ID"], "semarc-test-client")
        steps = {step["name"]: step for step in scenario["steps"]}
        self.assertNotIn("external", steps["GET /oauth/google returns an authorization URL"])
        self.assertEqual(steps["OAuth state is bound to its provider"]["expect"], 422)
        created = steps["Google sign-in creates an account"]
        self.assertEqual(created["external"], "oauth")
        self.assertEqual(created["body"]["code"], "google.user@example.com|1|Google User")
        self.assertEqual(created["equals"]["data.user.role"], "user")
        self.assertEqual(steps["linking disables the password of an unverified account"]["expect"], 422)

    def test_scenario_without_oauth_has_no_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ir = compile_file(ROOT / "tests" / "fixtures" / "edge_auth.sem", Path(tmpdir) / "out", "php", generate=False).ir
        self.assertNotIn("env", ApiScenarioBuilder().build(ir))

    def test_implicit_user_has_no_name_field(self):
        self.assertIsNone(plan(OAUTH)["auth"]["features"]["oauth"]["name_field"])


class OAuthValidationTests(unittest.TestCase):
    def assert_rejected(self, source: str, message: str) -> None:
        with self.assertRaises(SemanticValidationError) as raised:
            plan(source)
        self.assertIn(message, str(raised.exception))

    def test_requires_jwt(self):
        self.assert_rejected(OAUTH.replace("AUTH JWT\n", "") + "MODEL Post\n    title STRING\n", "USE auth.oauth.google requires AUTH JWT")

    def test_unknown_provider(self):
        self.assert_rejected(OAUTH + "USE auth.oauth.myspace\n", "Unsupported OAuth provider: auth.oauth.myspace")

    def test_required_user_fields_must_be_optional(self):
        self.assert_rejected(OAUTH + "MODEL User\n    name STRING\n    age INTEGER\n", "User.age must be OPTIONAL")

    def test_user_cannot_reference_another_model(self):
        source = OAUTH + "MODEL Team\n    title STRING\n\nRELATION Team HAS_MANY User\n"
        self.assert_rejected(source, "cannot create User records that reference another model")

    def test_name_and_optional_fields_are_accepted(self):
        ir = plan(OAUTH + "MODEL User\n    name STRING\n    bio TEXT OPTIONAL\n")
        self.assertEqual(ir["auth"]["features"]["oauth"]["name_field"], "name")


if __name__ == "__main__":
    unittest.main()

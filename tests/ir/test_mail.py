import tempfile
import unittest
from pathlib import Path

from semarc.generator.utils.api_scenario import ApiScenarioBuilder
from semarc.generator.utils.project_runtime import docker_compose, env_values
from semarc.generator.utils.resource_views import input_fields, mail_enabled, model_by_name
from tests.support import ROOT, compile_file


class MailPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_file(ROOT / "tests" / "fixtures" / "edge_mail.sem", Path(tmpdir) / "out", "php", generate=False)
        cls.ir = context.ir
        cls.routes = {(route["method"], route["path"]): route for route in cls.ir["routes"]}

    def test_features(self):
        features = self.ir["auth"]["features"]
        self.assertEqual(features["password_reset"], {"table": "password_resets", "ttl_seconds": 3600})
        self.assertEqual(
            features["email_verification"],
            {"table": "email_verifications", "ttl_seconds": 86400, "field": "email_verified_at"},
        )
        self.assertTrue(mail_enabled(self.ir))

    def test_routes_and_access(self):
        expected = {
            ("POST", "/password/forgot"): ("auth_forgot_password", "public"),
            ("POST", "/password/reset"): ("auth_reset_password", "public"),
            ("POST", "/email/verify"): ("auth_verify_email", "public"),
            ("POST", "/email/resend"): ("auth_resend_verification", "protected"),
        }
        for key, (kind, access) in expected.items():
            with self.subTest(route=key):
                self.assertEqual(self.routes[key]["operation"]["kind"], kind)
                self.assertEqual(self.routes[key]["access"], access)

    def test_verified_field_is_managed(self):
        user = model_by_name(self.ir, "User")
        verified = next(item for item in user["fields"] if item["name"] == "email_verified_at")
        self.assertEqual((verified["type"], verified["writable"]), ("DATETIME", False))
        self.assertNotIn("email_verified_at", input_fields(user))

    def test_token_tables_cascade(self):
        tables = {migration["table"]: migration for migration in self.ir["migrations"]["tables"] if migration.get("internal")}
        self.assertTrue({"password_resets", "email_verifications", "refresh_tokens"} <= set(tables))
        for name in ("password_resets", "email_verifications"):
            foreign_keys = tables[name]["foreign_keys"]
            self.assertEqual([(fk["column"], fk["on_delete"]) for fk in foreign_keys], [("user_id", "CASCADE")])

    def test_runtime_includes_mail(self):
        env = env_values(self.ir)
        self.assertEqual(env["MAIL_DRIVER"], "log")
        self.assertIn("APP_URL", env)
        self.assertIn("axllent/mailpit", docker_compose(self.ir, 8000))

    def test_scenario_reads_mail(self):
        steps = ApiScenarioBuilder().build(self.ir)["steps"]
        mail = [step["mail"] for step in steps if "mail" in step]
        self.assertEqual([item["save"] for item in mail], ["verify_token", "reset_token"])
        named = {step["name"]: step for step in steps if "name" in step}
        self.assertEqual(named["forgot password hides unknown accounts"]["expect"], 202)
        self.assertEqual(named["reset token is single use"]["expect"], 422)
        self.assertEqual(named["verification token is single use"]["expect"], 422)
        self.assertEqual(named["login after password reset"]["expect"], 200)


class NoMailTests(unittest.TestCase):
    def test_plain_auth_has_no_mail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ir = compile_file(ROOT / "tests" / "fixtures" / "edge_auth.sem", Path(tmpdir) / "out", "php", generate=False).ir
        self.assertFalse(mail_enabled(ir))
        self.assertNotIn("MAIL_DRIVER", env_values(ir))
        self.assertNotIn("mailpit", docker_compose(ir, 8000))
        self.assertFalse(any("mail" in step for step in ApiScenarioBuilder().build(ir)["steps"]))


if __name__ == "__main__":
    unittest.main()

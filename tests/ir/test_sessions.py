import tempfile
import unittest
from pathlib import Path

from semarc.generator.utils.api_scenario import ApiScenarioBuilder
from semarc.generator.utils.openapi import OpenApiBuilder
from semarc.generator.utils.project_runtime import docker_compose, env_values
from tests.support import ROOT, compile_file


class SessionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmpdir:
            cls.ir = compile_file(ROOT / "tests" / "fixtures" / "edge_session.sem", Path(tmpdir) / "out", "php", generate=False).ir
        cls.routes = {(route["method"], route["path"]): route for route in cls.ir["routes"]}

    def test_features(self):
        features = self.ir["auth"]["features"]
        self.assertEqual(self.ir["auth"]["strategy"], "SESSION")
        self.assertIsNone(features["refresh_tokens"])
        self.assertEqual(
            features["sessions"],
            {"table": "sessions", "ttl_seconds": 1209600, "cookie": "session", "csrf_cookie": "csrf_token", "csrf_header": "X-CSRF-Token"},
        )

    def test_routes(self):
        self.assertNotIn(("POST", "/token/refresh"), self.routes)
        self.assertEqual(self.routes[("POST", "/logout")]["access"], "protected")
        self.assertEqual(self.routes[("POST", "/login")]["access"], "public")

    def test_sessions_table(self):
        tables = {table["table"]: table for table in self.ir["migrations"]["tables"]}
        self.assertNotIn("refresh_tokens", tables)
        fields = [item["name"] for item in tables["sessions"]["fields"]]
        self.assertEqual(fields, ["token_hash", "csrf_hash", "expires_at", "revoked_at"])
        self.assertEqual(tables["sessions"]["foreign_keys"][0]["on_delete"], "CASCADE")

    def test_env(self):
        env = env_values(self.ir)
        self.assertEqual(env["SESSION_TTL"], "1209600")
        self.assertNotIn("JWT_REFRESH_TTL", env)

    def test_redis_rate_limit_store(self):
        self.assertEqual(self.ir["auth"]["rate_limit"]["store"], "redis")
        env = env_values(self.ir)
        self.assertEqual((env["RATE_LIMIT_STORE"], env["REDIS_URL"]), ("redis", "redis://127.0.0.1:6379/0"))
        compose = docker_compose(self.ir, 8000)
        self.assertIn("image: redis:7.4.2-alpine", compose)
        self.assertIn("      redis:\n        condition: service_healthy", compose)
        self.assertIn("TRUSTED_PROXIES: ${TRUSTED_PROXIES:-}", compose)

    def test_openapi(self):
        document = OpenApiBuilder().build(self.ir)
        self.assertEqual(set(document["components"]["securitySchemes"]), {"sessionCookie", "csrfHeader"})
        create = document["paths"]["/posts"]["post"]
        self.assertEqual(create["security"], [{"sessionCookie": [], "csrfHeader": []}])
        self.assertIn("403", create["responses"])
        self.assertIn("Session", document["components"]["schemas"])

    def test_scenario(self):
        scenario = ApiScenarioBuilder().build(self.ir)
        self.assertEqual(scenario["session"], {"cookie": "session", "csrf_cookie": "csrf_token", "csrf_header": "X-CSRF-Token"})
        steps = {step["name"]: step for step in scenario["steps"]}
        self.assertEqual(steps["register"]["save"]["token"], "data.csrf_token")
        self.assertEqual((steps["unsafe requests need the CSRF header"]["expect"], steps["unsafe requests need the CSRF header"]["csrf"]), (403, False))
        self.assertEqual(steps["ended session is rejected"]["expect"], 401)
        self.assertEqual(steps["password change ends every session"]["expect"], 401)
        self.assertFalse(any(step.get("path") == "/token/refresh" for step in scenario["steps"]))


if __name__ == "__main__":
    unittest.main()

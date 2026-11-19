import tempfile
import unittest
from pathlib import Path

from semarc.generator.utils.api_scenario import ApiScenarioBuilder
from semarc.generator.utils.resource_views import input_fields, model_by_name
from tests.support import ROOT, compile_file


class RolesPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_file(ROOT / "tests" / "fixtures" / "edge_roles.sem", Path(tmpdir) / "out", "php", generate=False)
        cls.ir = context.ir
        cls.routes = {(route["method"], route["path"]): route for route in cls.ir["routes"]}

    def test_roles_feature_collects_route_roles(self):
        self.assertEqual(
            self.ir["auth"]["features"]["roles"],
            {"default": "user", "admin": "admin", "names": ["admin", "editor", "user"]},
        )

    def test_role_routes_are_protected(self):
        route = self.routes[("POST", "/sections")]
        self.assertEqual(route["roles"], ["admin", "editor"])
        self.assertEqual(route["access"], "protected")
        self.assertEqual(self.routes[("GET", "/articles")]["roles"], [])

    def test_role_management_route(self):
        route = self.routes[("PUT", "/users/{id}/role")]
        self.assertEqual(route["operation"], {"kind": "auth_set_role", "model": "User", "parameter": "id"})
        self.assertEqual(route["roles"], ["admin"])

    def test_role_field_is_managed_with_default(self):
        user = model_by_name(self.ir, "User")
        role = next(item for item in user["fields"] if item["name"] == "role")
        self.assertEqual((role["writable"], role["default"]), (False, "user"))
        self.assertNotIn("role", input_fields(user))

    def test_scenario_checks_roles(self):
        steps = {step["name"]: step for step in ApiScenarioBuilder().build(self.ir)["steps"]}
        self.assertEqual(steps["bootstrap admin registers"]["equals"], {"data.user.role": "admin"})
        self.assertEqual(steps["POST /sections requires role admin, editor"]["expect"], 403)
        self.assertEqual(steps["create Section"]["auth_as"], "admin_token")
        self.assertEqual(steps["changing a role requires admin"]["expect"], 403)
        self.assertEqual(steps["admin may update another user's Article"]["expect"], 200)


if __name__ == "__main__":
    unittest.main()

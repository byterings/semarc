import tempfile
import unittest

from generator.utils.api_scenario import ApiScenarioBuilder
from tests.ir.test_resource_plan import BLOG
from tests.support import compile_source


def build(source: str) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmpdir:
        ir = compile_source(source, tmpdir, "php", generate=False).ir
    return ApiScenarioBuilder().build(ir)["steps"]


def step(steps: list[dict], name: str) -> dict:
    return next(item for item in steps if item["name"] == name)


class ApiScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steps = build(BLOG)

    def test_scenario_is_deterministic(self):
        self.assertEqual(build(BLOG), self.steps)

    def test_cors_is_checked_for_simple_and_preflight_requests(self):
        simple = step(self.steps, "CORS headers on requests from a browser")
        preflight = step(self.steps, "CORS preflight")
        self.assertEqual(simple["expect_headers"], {"access-control-allow-origin": "*"})
        self.assertEqual(preflight["method"], "OPTIONS")
        self.assertEqual(preflight["expect"], [200, 204])

    def test_experience_endpoints_come_first(self):
        self.assertEqual([item["path"] for item in self.steps[:3]], ["/", "/health", "/routes"])

    def test_registration_saves_token_and_hides_secret(self):
        register = step(self.steps, "register")
        self.assertEqual(register["expect"], 201)
        self.assertEqual(register["save"], {"token": "data.access_token", "user_id": "data.user.id"})
        self.assertEqual(register["absent"], ["data.user.password"])
        self.assertGreaterEqual(len(register["body"]["password"]), 8)

    def test_protected_create_is_checked_without_and_with_token(self):
        self.assertEqual(step(self.steps, "create Post requires token")["expect"], 401)
        create = step(self.steps, "create Post")
        self.assertTrue(create["auth"])
        self.assertNotIn("user_id", create["body"])
        self.assertEqual(create["equals"]["data.user_id"], {"$ref": "user_id"})

    def test_validation_and_conflict_checks(self):
        self.assertEqual(step(self.steps, "create Tag rejects empty body")["expect"], 422)
        self.assertEqual(step(self.steps, "create Tag rejects duplicate")["expect"], 409)
        self.assertEqual(step(self.steps, "update Post rejects invalid value")["body"], {"title": 12345})

    def test_string_samples_respect_max_length(self):
        create = step(self.steps, "create Post")
        self.assertLessEqual(len(create["body"]["title"]), 120)

    def test_custom_routes_expect_not_implemented(self):
        self.assertEqual(step(self.steps, "custom GET /stats is not implemented")["expect"], 501)

    def test_deletes_run_last_and_verify_removal(self):
        names = [item["name"] for item in self.steps]
        self.assertGreater(names.index("delete Post"), names.index("replace Post"))
        self.assertEqual(step(self.steps, "read deleted Post")["expect"], 404)

    def test_auth_model_records_do_not_replace_the_registered_user(self):
        source = BLOG.replace("ROUTE GET /stats\n", "ROUTE GET /stats\nROUTE POST /users\nROUTE DELETE /users/{id}\n")
        steps = build(source)
        names = [item["name"] for item in steps]
        self.assertNotIn("delete User blocked by dependents", names)
        self.assertIn("create User", names)
        self.assertEqual(step(steps, "create User")["save"], {"user_record_id": "data.id"})

    def test_login_rate_limit_is_exceeded_last(self):
        self.assertEqual(self.steps[-1]["name"], "login is rate limited")
        self.assertEqual(self.steps[-1]["expect"], 429)
        self.assertEqual(self.steps[-2]["expect"], [401, 429])
        logins = [item for item in self.steps if item["method"] == "POST" and item["path"] == "/login"]
        self.assertEqual(len(logins), 11)

    def test_list_routes_check_filters_and_sorting(self):
        matching = step(self.steps, "filter Tag by label")
        self.assertEqual(matching["path"], "/tags?label=label+1")
        self.assertEqual(matching["equals"], {"meta.total": 1})
        self.assertEqual(step(self.steps, "filter Tag by label without matches")["equals"], {"meta.total": 0})
        self.assertEqual(step(self.steps, "sort Tag rejects unknown field")["expect"], 422)
        self.assertEqual(step(self.steps, "filter Tag rejects invalid value")["path"], "/tags?id=not-a-number")
        self.assertNotIn("filter User by email", [item["name"] for item in self.steps])

    def test_date_samples_use_iso_formats(self):
        source = "PROJECT Events\n\nDATABASE SQLITE\n\nMODEL Event\n    starts_on DATE\n    begins_at DATETIME\n\nROUTE POST /events\n"
        body = step(build(source), "create Event")["body"]
        self.assertRegex(body["starts_on"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(body["begins_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_other_users_cannot_change_owned_records(self):
        names = [item["name"] for item in self.steps]
        self.assertIn("register second user", names)
        forbidden = step(self.steps, "update Post of another user is forbidden")
        self.assertEqual(forbidden["expect"], 403)
        self.assertEqual(forbidden["auth_as"], "other_token")
        self.assertEqual(step(self.steps, "replace Post of another user is forbidden")["body"], step(self.steps, "create Post")["body"])
        self.assertNotIn("delete Post of another user is forbidden", names)

    def test_models_with_only_optional_fields_are_supported(self):
        source = """PROJECT School

DATABASE SQLITE

MODEL Student
    name STRING

MODEL Enrollment
    grade STRING OPTIONAL

RELATION Student HAS_MANY Enrollment

ROUTE POST /students
ROUTE POST /enrollments
"""
        create = step(build(source), "create Enrollment")
        self.assertEqual(create["body"], {"student_id": {"$ref": "student_id"}})
        self.assertNotIn("equals", create)

    def test_children_without_creatable_parents_are_skipped(self):
        source = """PROJECT Shop

DATABASE SQLITE

MODEL Product
    name STRING

MODEL Review
    body TEXT

RELATION Product HAS_MANY Review

ROUTE GET /products
ROUTE POST /reviews
"""
        names = [item["name"] for item in build(source)]
        self.assertNotIn("create Review", names)
        self.assertIn("list Product", names)


if __name__ == "__main__":
    unittest.main()

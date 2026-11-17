import tempfile
import unittest

from architecture.optimizer import ArchitectureOptimizer
from tests.support import compile_source


def table(name: str, references: list[str]) -> dict:
    return {
        "model": name.title(),
        "table": name,
        "fields": [],
        "foreign_keys": [
            {"table": name, "column": f"{reference[:-1]}_id", "references_table": reference, "references_column": "id"}
            for reference in references
        ],
    }


class MigrationOrderingTests(unittest.TestCase):
    def test_referenced_tables_are_created_first(self):
        migrations = {
            "tables": [
                table("orders", ["users", "products"]),
                table("users", []),
                table("products", []),
                table("order_items", ["orders", "products"]),
            ],
            "foreign_keys": [],
        }

        ordered = ArchitectureOptimizer().order_migrations(migrations)
        names = [entry["table"] for entry in ordered["tables"]]

        self.assertEqual(names, ["products", "users", "orders", "order_items"])
        self.assertEqual([entry["sequence"] for entry in ordered["tables"]], [1, 2, 3, 4])

    def test_ordering_is_independent_of_declaration_order(self):
        tables = [table("comments", ["posts"]), table("posts", ["users"]), table("users", [])]
        forward = ArchitectureOptimizer().order_migrations({"tables": tables})
        backward = ArchitectureOptimizer().order_migrations({"tables": list(reversed(tables))})

        self.assertEqual(forward, backward)
        self.assertEqual([entry["table"] for entry in forward["tables"]], ["users", "posts", "comments"])

    def test_cycles_are_reported(self):
        with self.assertRaises(ValueError):
            ArchitectureOptimizer().order_migrations({"tables": [table("a_items", ["b_items"]), table("b_items", ["a_items"])]})

    def test_compiled_ir_orders_child_tables_after_parents(self):
        source = """PROJECT Shop

DATABASE MYSQL

MODEL Order
    total INTEGER

MODEL Product
    name STRING

MODEL User
    email STRING

RELATION User HAS_MANY Order
RELATION Product HAS_MANY Order
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "php", generate=False)

        names = [entry["table"] for entry in context.ir["migrations"]["tables"]]
        self.assertLess(names.index("users"), names.index("orders"))
        self.assertLess(names.index("products"), names.index("orders"))


class DeduplicationTests(unittest.TestCase):
    def test_components_are_unique_by_name(self):
        ir = {
            "models": [],
            "repositories": [],
            "relationships": [],
            "controllers": [{"name": "AuthController"}, {"name": "AuthController"}],
            "services": [{"name": "TokenService"}, {"name": "TokenService"}, {"name": "PasswordHasher"}],
            "middlewares": [],
            "validators": [{"name": "Validator"}, {"name": "Validator"}],
            "migrations": {"tables": []},
        }

        optimized = ArchitectureOptimizer().optimize(ir)

        self.assertEqual([item["name"] for item in optimized["controllers"]], ["AuthController"])
        self.assertEqual([item["name"] for item in optimized["services"]], ["TokenService", "PasswordHasher"])
        self.assertEqual(len(optimized["validators"]), 1)


if __name__ == "__main__":
    unittest.main()

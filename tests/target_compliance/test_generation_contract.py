import tempfile
import unittest
from pathlib import Path

from architecture.contracts import (
    API_LAYER,
    AUTH_LAYER,
    BUSINESS_LAYER,
    CONFIGURATION_LAYER,
    ENTITY_LAYER,
    PERSISTENCE_LAYER,
    PROJECT_LAYER,
)
from tests.support import compile_source


CONTRACT_SOURCE = """PROJECT ContractAPI

TARGET PHP

DATABASE MYSQL

AUTH JWT

MODEL Customer
    name STRING
    email STRING

ROUTE POST /login
ROUTE GET /customers
"""


class GenerationContractComplianceTests(unittest.TestCase):
    def test_contract_contains_neutral_architecture_layers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(CONTRACT_SOURCE, tmpdir, "php", generate=True)
            contract = context.generation_contract

            self.assertEqual(
                contract.required_layers(),
                [
                    PROJECT_LAYER,
                    CONFIGURATION_LAYER,
                    ENTITY_LAYER,
                    PERSISTENCE_LAYER,
                    BUSINESS_LAYER,
                    API_LAYER,
                    AUTH_LAYER,
                ],
            )
            self.assertIn("entity:Customer", contract.components)
            self.assertIn("persistence:CustomerRepository", contract.components)
            self.assertIn("business:CustomerService", contract.components)
            self.assertIn("api:GET:/customers", contract.components)

    def test_php_target_wires_route_controller_service_repository_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(CONTRACT_SOURCE, tmpdir, "php", generate=True)
            output = Path(context.output_dir)

            self.assertTrue((output / "models" / "Customer.php").exists())
            self.assertTrue((output / "repositories" / "CustomerRepository.php").exists())
            self.assertTrue((output / "services" / "CustomerService.php").exists())
            self.assertTrue((output / "controllers" / "CustomerController.php").exists())

            routes = (output / "routes.php").read_text(encoding="utf-8")
            controller = (output / "controllers" / "CustomerController.php").read_text(encoding="utf-8")
            service = (output / "services" / "CustomerService.php").read_text(encoding="utf-8")
            repository = (output / "repositories" / "CustomerRepository.php").read_text(encoding="utf-8")

            self.assertIn("new CustomerController()", routes)
            self.assertIn("$controller->index()", routes)
            self.assertNotIn("json_encode(['data' => []])", routes)
            self.assertIn("new CustomerService()", controller)
            self.assertIn("new CustomerRepository()", service)
            self.assertIn("createCustomer", repository)
            self.assertIn("getCustomers", repository)
            self.assertNotIn("createUser", repository)

    def test_php_output_has_no_duplicate_app_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(CONTRACT_SOURCE, tmpdir, "php", generate=True)
            output = Path(context.output_dir)

            self.assertFalse((output / "app").exists())
            self.assertFalse((output / "routes" / "web.php").exists())

    def test_auth_generation_is_todo_scaffold_not_fake_token_runtime(self):
        for target in ["php", "fastapi", "nestjs"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmpdir:
                source = CONTRACT_SOURCE.replace("TARGET PHP", f"TARGET {target.upper()}")
                context = compile_source(source, tmpdir, target, generate=True)
                generated_text = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in Path(context.output_dir).rglob("*")
                    if path.is_file() and path.suffix in {".php", ".py", ".ts"}
                )

                self.assertIn("TODO", generated_text)
                self.assertNotIn("demo-token", generated_text)
                self.assertNotIn("base64_encode", generated_text)
                self.assertNotIn("base64.b64encode", generated_text)

    def test_fastapi_target_wires_router_service_repository_model(self):
        source = CONTRACT_SOURCE.replace("TARGET PHP", "TARGET FASTAPI")
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "fastapi", generate=True)
            output = Path(context.output_dir)

            self.assertTrue((output / "models" / "customer.py").exists())
            self.assertTrue((output / "repositories" / "customer_repository.py").exists())
            self.assertTrue((output / "services" / "customer_service.py").exists())
            self.assertTrue((output / "routers" / "customer.py").exists())
            self.assertFalse((output / "app").exists())

            router = (output / "routers" / "customer.py").read_text(encoding="utf-8")
            service = (output / "services" / "customer_service.py").read_text(encoding="utf-8")
            self.assertIn("CustomerService", router)
            self.assertIn("customer_service.list()", router)
            self.assertIn("CustomerRepository", service)

    def test_nestjs_target_wires_controller_service_repository_entity(self):
        source = CONTRACT_SOURCE.replace("TARGET PHP", "TARGET NESTJS")
        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "nestjs", generate=True)
            output = Path(context.output_dir)
            module = output / "src" / "modules" / "customers"

            self.assertTrue((module / "customer.model.ts").exists())
            self.assertTrue((module / "customers.repository.ts").exists())
            self.assertTrue((module / "customers.service.ts").exists())
            self.assertTrue((module / "customers.controller.ts").exists())

            service = (module / "customers.service.ts").read_text(encoding="utf-8")
            self.assertIn("CustomerRepository", service)
            self.assertIn("this.repository.findAll()", service)


if __name__ == "__main__":
    unittest.main()

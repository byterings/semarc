import tempfile
import time
import unittest
from pathlib import Path

from architecture.profiles import Profile, ProfileCompositionResolver, ProfileRegistry
from architecture.stdlib import ModuleDefinition, ModuleDependencyResolver, ModuleRegistry
from tests.support import compile_source


class StressSuiteTests(unittest.TestCase):
    def test_large_model_and_route_set_compiles(self):
        source = self._large_architecture_source(model_count=100, route_count=500)
        started = time.monotonic()

        with tempfile.TemporaryDirectory() as tmpdir:
            context = compile_source(source, tmpdir, "nestjs", generate=True)

        elapsed = time.monotonic() - started
        self.assertEqual(len(context.ast.models), 100)
        self.assertEqual(len(context.ast.routes), 500)
        self.assertLess(elapsed, 10)

    def test_long_module_dependency_chain_resolves(self):
        registry = ModuleRegistry()
        modules = []
        for index in range(50):
            dependency = [f"chain.module{index + 1}"] if index < 49 else []
            module = ModuleDefinition(
                f"chain.module{index}",
                "1.0",
                "chain",
                Path(f"chain{index}"),
                dependency,
            )
            registry.register(module)
            modules.append(module)

        resolved = ModuleDependencyResolver(registry).resolve([modules[0]])

        self.assertEqual(len(resolved), 50)
        self.assertEqual(resolved[-1].name, "chain.module49")

    def test_large_profile_inheritance_chain_resolves(self):
        registry = ProfileRegistry()
        for index in range(20):
            extends = [f"Profile{index - 1}"] if index > 0 else []
            registry.register(
                Profile(
                    name=f"Profile{index}",
                    extends=extends,
                    modules=[f"module.{index}"],
                )
            )

        profiles, modules = ProfileCompositionResolver(registry).resolve(["Profile19"])

        self.assertEqual(len(profiles), 20)
        self.assertEqual(len(modules), 20)
        self.assertEqual(modules[0], "module.0")
        self.assertEqual(modules[-1], "module.19")

    def _large_architecture_source(self, model_count: int, route_count: int) -> str:
        lines = [
            "PROJECT StressRelease",
            "",
            "DATABASE MYSQL",
            "",
        ]
        for index in range(model_count):
            lines.extend(
                [
                    f"MODEL Entity{index}",
                    "    name STRING",
                    "",
                ]
            )
        for index in range(route_count):
            lines.append(f"ROUTE GET /entity{index % model_count}s/route{index}")
        return "\n".join(lines) + "\n"

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_semantic_nodes() -> ModuleType:
    """Load local ast/nodes.py without shadowing Python's standard ast module."""

    module_name = "semarc_semantic_nodes"
    if module_name in sys.modules:
        return sys.modules[module_name]

    nodes_path = Path(__file__).parent / "ast" / "nodes.py"
    spec = importlib.util.spec_from_file_location(module_name, nodes_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load semantic AST nodes from {nodes_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_ast_builder() -> ModuleType:
    """Load local ast/ast_builder.py despite the stdlib ast module name."""

    module_name = "semarc_ast_builder"
    if module_name in sys.modules:
        return sys.modules[module_name]

    builder_path = Path(__file__).parent / "ast" / "ast_builder.py"
    spec = importlib.util.spec_from_file_location(module_name, builder_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load AST builder from {builder_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

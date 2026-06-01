import argparse
import json
import sys
from pathlib import Path

from compiler.context import CompilerContext
from compiler.contracts import CompilerContractError, ContractValidator
from compiler.passes.contract_pass import ContractPass
from compiler.passes.constraint_pass import ConstraintPass
from compiler.passes.diagnostic_report_pass import DiagnosticReportPass
from compiler.passes.expansion_pass import ExpansionPass
from compiler.passes.generation_pass import GenerationPass
from compiler.passes.ir_pass import IRPass
from compiler.passes.lexing_pass import LexingPass
from compiler.passes.optimization_pass import OptimizationPass
from compiler.passes.parsing_pass import ParsingPass
from compiler.passes.relationship_pass import RelationshipPass
from compiler.passes.stdlib_pass import StdlibPass
from compiler.passes.validation_pass import ValidationPass
from parser.parser import ParserError
from validator.validator import SemanticValidationError


def compile_semantic_file(
    source_path: Path,
    debug: bool = False,
    target_override: str | None = None,
) -> CompilerContext:
    context = CompilerContext(source_path=source_path, debug=debug, target_override=target_override)

    LexingPass().run(context)
    if debug:
        print_debug("TOKENS", tokens_to_debug(context.tokens))

    ParsingPass().run(context)
    ContractPass().validate_ast(context)
    if debug:
        print_debug("AST", ast_to_debug(context.ast))

    StdlibPass().run(context)
    ValidationPass().run(context)
    RelationshipPass().run(context)
    ConstraintPass().run(context)
    if debug:
        print_debug("COMPILER PASSES", context.compiler_passes)
        print_modules_summary(context)
        print_debug("RELATIONSHIP GRAPH", context.relationship_graph)
        print_debug("MIGRATION PLAN", context.migration_plan)
        print_constraint_summary(context)

    ExpansionPass().run(context)
    if debug:
        print_debug("TARGET PROFILE", context.target_profile)
        print_debug("DEPENDENCY GRAPH", context.dependency_graph.to_debug())
        print_debug("ARCHITECTURE EXPANSION", expansion_to_debug(context.expanded_architecture))

    IRPass().run(context)
    OptimizationPass().run(context)
    ContractPass().validate_ir(context)
    if debug:
        print_integrity_report(context)
        print_debug("ARCHITECTURE IR", context.ir)

    GenerationPass().run(context)
    DiagnosticReportPass().run(context)
    ContractPass().validate_generation(context)
    if debug:
        print_debug("COMPILER PASSES COMPLETE", context.compiler_passes)
    return context


def main() -> int:
    arg_parser = argparse.ArgumentParser(description="Compile semantic architecture into backend code.")
    arg_parser.add_argument("semantic_file", help="Path to the .sem source file")
    arg_parser.add_argument("--target", help="Override semantic TARGET for this run")
    arg_parser.add_argument("--debug", action="store_true", help="Print tokens, AST, and Architecture IR")
    args = arg_parser.parse_args()

    source_path = Path(args.semantic_file)
    if not source_path.exists():
        print(f"Semantic source file not found: {source_path}")
        return 1

    try:
        context = compile_semantic_file(
            source_path,
            debug=args.debug,
            target_override=args.target,
        )
    except ParserError as error:
        print(f"Parse error: {error}")
        return 1
    except SemanticValidationError as error:
        print(error)
        return 1
    except CompilerContractError as error:
        print(f"[Contract Error]\n{error}")
        return 1

    if context.resolved_modules:
        print("Modules Loaded:")
        for module in context.resolved_modules:
            print(f"* {module.name}")
        print("Compilation Successful")
    print(f"Generated {context.target_profile['target']} backend in output/")
    return 0


def tokens_to_debug(token_lines) -> list:
    return [
        [
            {
                "type": token.token_type,
                "value": token.value,
                "line": token.line,
                "column": token.column,
                "indent": token.indent,
            }
            for token in line
        ]
        for line in token_lines
    ]


def print_debug(title: str, payload) -> None:
    print(f"\n--- {title} ---")
    print(json.dumps(payload, indent=2))


def print_integrity_report(context: CompilerContext) -> None:
    validator = ContractValidator()
    leakage = validator.detect_target_leakage(context.ir)
    graph_diagnostics = context.dependency_graph.diagnostics()

    print("\n[IR Validation]")
    if leakage:
        print("FAIL: Target-specific leakage detected")
        print("Markers: " + ", ".join(leakage))
    else:
        print("PASS: No target-specific leakage detected")

    print("\n[Dependency Graph]")
    print(f"Nodes: {graph_diagnostics['node_count']}")
    print(f"Dependencies: {graph_diagnostics['dependency_count']}")
    print(f"Orphans: {len(graph_diagnostics['orphan_nodes'])}")
    print(f"Duplicate dependencies: {len(graph_diagnostics['duplicate_dependencies'])}")


def print_constraint_summary(context: CompilerContext) -> None:
    report = context.architecture_report
    print("\n[Constraint Engine]")
    print(f"Rules Executed: {report.get('rules_executed', 0)}")
    print(f"Warnings: {len(report.get('warnings', []))}")
    print(f"Recommendations: {len(report.get('recommendations', []))}")
    print(f"Errors: {len(report.get('errors', []))}")
    print(f"Architecture Score: {report.get('score', 0)}")


def print_modules_summary(context: CompilerContext) -> None:
    print("\n[Stdlib]")
    print("Modules Loaded:")
    if not context.resolved_modules:
        print("- none")
        return
    for module in context.resolved_modules:
        print(f"- {module.name}")


def ast_to_debug(value):
    if hasattr(value, "debug"):
        debug_value = value.debug()
        return {key: ast_to_debug(item) for key, item in debug_value.items()}
    if isinstance(value, list):
        return [ast_to_debug(item) for item in value]
    if isinstance(value, dict):
        return {key: ast_to_debug(item) for key, item in value.items()}
    return value


def expansion_to_debug(value):
    if hasattr(value, "debug"):
        return ast_to_debug(value)
    if isinstance(value, list):
        return [expansion_to_debug(item) for item in value]
    if isinstance(value, dict):
        return {key: expansion_to_debug(item) for key, item in value.items()}
    return value


if __name__ == "__main__":
    raise SystemExit(main())

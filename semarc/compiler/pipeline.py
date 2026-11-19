"""The SEMARC compiler pipeline: every pass from source to generated project."""
import json
from pathlib import Path

from semarc.compiler.context import CompilerContext
from semarc.compiler.contracts import ContractValidator
from semarc.compiler.passes.contract_pass import ContractPass
from semarc.compiler.passes.constraint_pass import ConstraintPass
from semarc.compiler.passes.diagnostic_report_pass import DiagnosticReportPass
from semarc.compiler.passes.architecture_analysis_pass import ArchitectureAnalysisPass
from semarc.compiler.passes.expansion_pass import ExpansionPass
from semarc.compiler.passes.generation_pass import GenerationPass
from semarc.compiler.passes.ir_pass import IRPass
from semarc.compiler.passes.lexing_pass import LexingPass
from semarc.compiler.passes.module_constraint_pass import ModuleConstraintPass
from semarc.compiler.passes.optimization_pass import OptimizationPass
from semarc.compiler.passes.parsing_pass import ParsingPass
from semarc.compiler.passes.profile_pass import ProfilePass
from semarc.compiler.passes.relationship_pass import RelationshipPass
from semarc.compiler.passes.stdlib_pass import StdlibPass
from semarc.compiler.passes.validation_pass import ValidationPass


def compile_semantic_file(
    source_path: Path,
    debug: bool = False,
    target_override: str | None = None,
    output_dir: str = "output",
    force_output: bool = False,
    generate: bool = True,
) -> CompilerContext:
    context = CompilerContext(
        source_path=source_path,
        output_dir=output_dir,
        force_output=force_output,
        debug=debug,
        target_override=target_override,
    )

    LexingPass().run(context)
    if debug:
        print_debug("TOKENS", tokens_to_debug(context.tokens))

    ParsingPass().run(context)
    ContractPass().validate_ast(context)
    if debug:
        print_debug("AST", ast_to_debug(context.ast))

    ProfilePass().run(context)
    StdlibPass().run(context)
    ValidationPass().run(context)
    ModuleConstraintPass().run(context)
    RelationshipPass().run(context)
    ConstraintPass().run(context)
    ArchitectureAnalysisPass().run(context)
    if debug:
        print_debug("COMPILER PASSES", context.compiler_passes)
        print_modules_summary(context)
        print_debug("RELATIONSHIP GRAPH", context.relationship_graph)
        print_debug("MIGRATION PLAN", context.migration_plan)
        print_constraint_summary(context)
        print_architecture_analysis_summary(context)

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

    if not generate:
        return context

    GenerationPass().run(context)
    DiagnosticReportPass().run(context)
    ContractPass().validate_generation(context)
    if debug:
        print_debug("COMPILER PASSES COMPLETE", context.compiler_passes)
    return context


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


def print_architecture_analysis_summary(context: CompilerContext) -> None:
    report = context.architecture_analysis_report
    print("\n[Architecture Analysis]")
    print(f"Rules Executed: {report.get('rules_executed', 0)}")
    print(f"Warnings: {len(report.get('warnings', []))}")
    print(f"Recommendations: {len(report.get('recommendations', []))}")


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



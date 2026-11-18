"""Command line interface for SEMARC.

    semarc build app.sem [--target T] [--output DIR] [--force] [--debug]
    semarc check app.sem [--target T]
    semarc targets
    semarc version

`python3 main.py app.sem [options]` remains available and behaves like `semarc build`.
"""
import argparse
from pathlib import Path

from architecture.contracts import ContractError
from compiler.context import CompilerContext
from compiler.contracts import CompilerContractError
from compiler.passes.generation_pass import GenerationBlockedError
from compiler.pipeline import compile_semantic_file
from compiler.version import SEMARC_VERSION
from generator.output_directory import OutputDirectoryError
from parser.parser import ParserError
from validator.validator import SemanticValidationError

COMPILER_ERRORS = {
    ParserError: "Parse error: {error}",
    SemanticValidationError: "{error}",
    CompilerContractError: "[Contract Error]\n{error}",
    ContractError: "[Generation Contract Error]\n{error}",
    GenerationBlockedError: "[Generation Blocked]\n{error}",
    OutputDirectoryError: "[Output Error]\n{error}",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="semarc", description="Compile semantic architecture into runnable backend projects.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="Generate a project from a .sem specification")
    _add_build_arguments(build)

    check = commands.add_parser("check", help="Validate a specification and show the planned API without generating")
    check.add_argument("semantic_file", help="Path to the .sem source file")
    check.add_argument("--target", help="Override semantic TARGET for this run")

    commands.add_parser("targets", help="List available targets")
    commands.add_parser("version", help="Print the SEMARC version")

    args = parser.parse_args(argv)
    if args.command == "build":
        return build_command(args)
    if args.command == "check":
        return check_command(args)
    if args.command == "targets":
        return targets_command()
    print(f"semarc {SEMARC_VERSION}")
    return 0


def legacy_main(argv: list[str] | None = None) -> int:
    """`python3 main.py app.sem [options]`, equivalent to `semarc build`."""
    parser = argparse.ArgumentParser(description="Compile semantic architecture into backend code.")
    _add_build_arguments(parser)
    return build_command(parser.parse_args(argv))


def build_command(args: argparse.Namespace) -> int:
    source_path = Path(args.semantic_file)
    if not source_path.exists():
        print(f"Semantic source file not found: {source_path}")
        return 1
    context = _compile(
        source_path,
        debug=args.debug,
        target_override=args.target,
        output_dir=args.output,
        force_output=args.force,
    )
    if context is None:
        return 1

    if context.resolved_modules:
        print("Modules Loaded:")
        for module in context.resolved_modules:
            print(f"* {module.name}")
        if context.dependency_resolved_modules:
            print("Resolved Through Dependencies:")
            for module in context.dependency_resolved_modules:
                print(f"* {module.name}")
        if context.module_requirements:
            print("Requirements:")
            for requirement in context.module_requirements:
                print(f"* {requirement}")
        if context.module_conflicts:
            print("Conflicts:")
            for conflict in context.module_conflicts:
                print(f"* {conflict}")
        print("Compilation Successful")
    print(f"Generated {context.target_profile['target']} backend in {context.output_dir}/")
    return 0


def check_command(args: argparse.Namespace) -> int:
    source_path = Path(args.semantic_file)
    if not source_path.exists():
        print(f"Semantic source file not found: {source_path}")
        return 1
    context = _compile(source_path, target_override=args.target, generate=False)
    if context is None:
        return 1

    ir = context.ir
    database = ir["config"]["database"]["engine"]
    print(f"Project {ir['project']} (target {context.target_profile['target']}, database {database})")
    if ir.get("auth"):
        print(f"Auth: JWT on model {ir['auth']['model']}")
    print("Models: " + ", ".join(model["name"] for model in ir["models"]))
    print("Routes:")
    width = max((len(route["path"]) for route in ir["routes"]), default=10)
    for route in ir["routes"]:
        operation = route["operation"]
        subject = operation.get("model") or ""
        owner = " (owner only)" if operation.get("owner_only") else ""
        print(f"  {route['method']:<7}{route['path']:<{width + 2}}{route['access']:<11}{operation['kind']} {subject}{owner}".rstrip())

    report = context.architecture_report
    analysis = context.architecture_analysis_report
    findings = [
        ("error", item) for item in report.get("errors", [])
    ] + [
        ("warning", item) for item in report.get("warnings", []) + analysis.get("warnings", [])
    ] + [
        ("recommendation", item) for item in report.get("recommendations", []) + analysis.get("recommendations", [])
    ]
    print(f"Diagnostics: score {report.get('score', 0)}, {len(findings)} finding(s)")
    for level, item in findings:
        print(f"  {level} {item['code']}: {item['message']}")
    return 1 if report.get("errors") else 0


def targets_command() -> int:
    from generator.targets import TargetRegistry

    for target in TargetRegistry.builtins().all():
        print(f"{target.name:<10}{target.language:<12}{target.description}")
    return 0


def _compile(source_path: Path, **options) -> CompilerContext | None:
    try:
        return compile_semantic_file(source_path, **options)
    except tuple(COMPILER_ERRORS) as error:
        template = next(message for error_type, message in COMPILER_ERRORS.items() if isinstance(error, error_type))
        print(template.format(error=error))
        return None


def _add_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("semantic_file", help="Path to the .sem source file")
    parser.add_argument("--target", help="Override semantic TARGET for this run")
    parser.add_argument("--output", default="output", help="Directory for the generated project (default: output)")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace a non-empty output directory that was not generated by SEMARC",
    )
    parser.add_argument("--debug", action="store_true", help="Print tokens, AST, and Architecture IR")

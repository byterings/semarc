import py_compile
import shutil
import subprocess
from pathlib import Path

from compiler.context import CompilerContext
from compiler.passes.architecture_analysis_pass import ArchitectureAnalysisPass
from compiler.passes.constraint_pass import ConstraintPass
from compiler.passes.contract_pass import ContractPass
from compiler.passes.diagnostic_report_pass import DiagnosticReportPass
from compiler.passes.expansion_pass import ExpansionPass
from compiler.passes.generation_pass import GenerationPass
from compiler.passes.ir_pass import IRPass
from compiler.passes.lexing_pass import LexingPass
from compiler.passes.module_constraint_pass import ModuleConstraintPass
from compiler.passes.optimization_pass import OptimizationPass
from compiler.passes.parsing_pass import ParsingPass
from compiler.passes.profile_pass import ProfilePass
from compiler.passes.relationship_pass import RelationshipPass
from compiler.passes.stdlib_pass import StdlibPass
from compiler.passes.validation_pass import ValidationPass


ROOT = Path(__file__).resolve().parents[1]


def compile_source(source: str, tmpdir: str | Path, target: str, generate: bool = True) -> CompilerContext:
    tmpdir = Path(tmpdir)
    source_path = tmpdir / "app.sem"
    output_dir = tmpdir / "out"
    source_path.write_text(source, encoding="utf-8")
    return compile_file(source_path, output_dir, target, generate)


def compile_file(source_path: Path, output_dir: Path, target: str, generate: bool = True) -> CompilerContext:
    context = CompilerContext(
        source_path=source_path,
        output_dir=str(output_dir),
        target_override=target,
    )
    for compiler_pass in [
        LexingPass(),
        ParsingPass(),
        ContractPass(),
        ProfilePass(),
        StdlibPass(),
        ValidationPass(),
        ModuleConstraintPass(),
        RelationshipPass(),
        ConstraintPass(),
        ArchitectureAnalysisPass(),
        ExpansionPass(),
        IRPass(),
        OptimizationPass(),
    ]:
        if isinstance(compiler_pass, ContractPass):
            compiler_pass.validate_ast(context)
        else:
            compiler_pass.run(context)

    ContractPass().validate_ir(context)

    if generate:
        GenerationPass().run(context)
        DiagnosticReportPass().run(context)
        ContractPass().validate_generation(context)

    return context


def generated_code_files(output_dir: Path) -> list[Path]:
    suffixes = {".php", ".py", ".sql", ".ts", ".json", ".md", ".txt", ".yml", ".example"}
    names = {"Dockerfile", ".htaccess"}
    return sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and (path.suffix in suffixes or path.name in names)
    )


def generated_file_map(output_dir: Path) -> dict[str, str]:
    return {
        str(path.relative_to(output_dir)): path.read_text(encoding="utf-8")
        for path in generated_code_files(output_dir)
    }


class GeneratorValidationSuite:
    REQUIRED_FILES = {
        "php": [
            "README.md",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            "generator_manifest.json",
            "public/index.php",
            "routes.php",
            "config/database.php",
        ],
        "fastapi": [
            "README.md",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            "generator_manifest.json",
            "requirements.txt",
            "app/main.py",
            "main.py",
            "config/settings.py",
        ],
        "nestjs": [
            "README.md",
            ".env.example",
            "Dockerfile",
            "docker-compose.yml",
            "generator_manifest.json",
            "package.json",
            "nest-cli.json",
            "tsconfig.json",
            "src/app.module.ts",
        ],
    }

    REQUIRED_DIRECTORIES = {
        "php": [
            "public",
            "app/Controllers",
            "app/Services",
            "app/Models",
            "routes",
            "storage",
            "tests",
            "controllers",
            "models",
            "services",
            "repositories",
            "middleware",
            "migrations",
            "config",
        ],
        "fastapi": [
            "app",
            "app/routers",
            "app/models",
            "app/schemas",
            "app/services",
            "tests",
            "config",
            "routers",
            "models",
            "schemas",
            "services",
            "repositories",
            "middleware",
            "migrations",
        ],
        "nestjs": ["src", "src/modules", "test"],
    }

    def validate(self, context: CompilerContext, target: str) -> None:
        output_dir = Path(context.output_dir)
        self.validate_required_files(output_dir, target)
        self.validate_non_empty_files(output_dir)
        self.validate_structure(output_dir, target)
        self.validate_no_duplicate_output_paths(context)
        self.validate_no_template_placeholders(output_dir)
        self.validate_syntax(output_dir, target)

    def validate_required_files(self, output_dir: Path, target: str) -> None:
        for relative_path in self.REQUIRED_FILES[target]:
            path = output_dir / relative_path
            if not path.exists():
                raise AssertionError(f"Missing required generated file: {relative_path}")

    def validate_non_empty_files(self, output_dir: Path) -> None:
        for path in generated_code_files(output_dir):
            if path.stat().st_size == 0:
                raise AssertionError(f"Generated file is empty: {path.relative_to(output_dir)}")

    def validate_structure(self, output_dir: Path, target: str) -> None:
        for relative_path in self.REQUIRED_DIRECTORIES[target]:
            path = output_dir / relative_path
            if not path.is_dir():
                raise AssertionError(f"Missing generated directory: {relative_path}")

    def validate_no_duplicate_output_paths(self, context: CompilerContext) -> None:
        paths = [component["created"] for component in context.generated_components]
        duplicates = sorted({path for path in paths if paths.count(path) > 1})
        if duplicates:
            raise AssertionError("Duplicate generated output paths: " + ", ".join(duplicates))

    def validate_no_template_placeholders(self, output_dir: Path) -> None:
        for path in generated_code_files(output_dir):
            content = path.read_text(encoding="utf-8")
            if "{{" in content or "}}" in content:
                raise AssertionError(f"Unresolved template placeholder in {path.relative_to(output_dir)}")

    def validate_syntax(self, output_dir: Path, target: str) -> None:
        if target == "php":
            self._validate_php_syntax(output_dir)
        elif target == "fastapi":
            self._validate_python_syntax(output_dir)
        elif target == "nestjs":
            self._validate_typescript_structure(output_dir)

    def _validate_php_syntax(self, output_dir: Path) -> None:
        php = shutil.which("php")
        if php is None:
            return
        for path in sorted(output_dir.rglob("*.php")):
            result = subprocess.run([php, "-l", str(path)], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise AssertionError(result.stderr or result.stdout)

    def _validate_python_syntax(self, output_dir: Path) -> None:
        for path in sorted(output_dir.rglob("*.py")):
            py_compile.compile(str(path), doraise=True)

    def _validate_typescript_structure(self, output_dir: Path) -> None:
        for path in sorted(output_dir.rglob("*.ts")):
            content = path.read_text(encoding="utf-8")
            if content.count("{") != content.count("}"):
                raise AssertionError(f"Unbalanced braces in {path.relative_to(output_dir)}")
            if path.relative_to(output_dir).parts[0] == "src" and "export " not in content:
                raise AssertionError(f"Missing TypeScript export in {path.relative_to(output_dir)}")

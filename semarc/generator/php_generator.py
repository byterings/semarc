from pathlib import Path

from semarc.generator.php.controller_generator import ControllerGenerator
from semarc.generator.php.core_generator import CoreGenerator
from semarc.generator.php.base import PhpFileWriter
from semarc.generator.php.migration_generator import MigrationGenerator
from semarc.generator.php.model_generator import ModelGenerator
from semarc.generator.php.project_generator import ProjectGenerator
from semarc.generator.php.repository_generator import RepositoryGenerator
from semarc.generator.php.routes_generator import RoutesGenerator
from semarc.generator.php.service_generator import ServiceGenerator
from semarc.generator.php.template_engine import TemplateEngine
from semarc.generator.project_files import ProjectFileWriter


class PhpGenerator:
    """Facade for modular PHP generators. Consumes Architecture IR only."""

    def __init__(self, output_dir: str = "output", debug: bool = False) -> None:
        self.output_dir = Path(output_dir)
        self.template_engine = TemplateEngine("php")
        self.debug = debug
        self.generated_components: list[dict[str, str]] = []

    def generate(self, ir: dict) -> None:
        self.generated_components = []
        self.output_dir.mkdir(parents=True, exist_ok=True)
        writer = PhpFileWriter(self.output_dir, self.template_engine, self._record)

        core = CoreGenerator(writer)
        sources = core.generate(ir)
        auth_sources = core.generate_auth(ir) if ir.get("auth") else {"core": [], "middleware": [], "controllers": []}
        sources += auth_sources["core"]
        sources += ModelGenerator(writer).generate(ir)
        sources += RepositoryGenerator(writer).generate(ir)
        sources += ServiceGenerator(writer).generate(ir)
        sources += auth_sources["middleware"]
        sources += auth_sources["controllers"]
        sources += ControllerGenerator(writer).generate(ir)
        MigrationGenerator(writer).generate(ir)
        RoutesGenerator(writer).generate(ir)
        ProjectGenerator(writer).generate(ir, sources)
        ProjectFileWriter(self.output_dir, self._record).write_manifest(ir, "php")

        if self.debug:
            print("\n[Generator]")
            for component in self.generated_components:
                print(f"Created: {component['created']}")
                print(f"Template: {component['template']}")

    def _record(self, path: Path, template: str) -> None:
        self.generated_components.append(
            {
                "created": path.relative_to(self.output_dir).as_posix(),
                "template": template,
            }
        )

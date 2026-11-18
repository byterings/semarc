from semarc.architecture.contracts import (
    ContractDefinition,
    ContractValidator,
    GeneratorArchitectureValidator,
    TargetContractAdapter,
)
from semarc.generator.output_directory import OutputDirectory
from semarc.generator.targets.factory import TargetGeneratorFactory
from semarc.generator.targets import TargetRegistry


class GenerationBlockedError(Exception):
    pass


class GenerationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("GenerationPass")
        self._ensure_no_diagnostic_errors(context)
        generator_name = context.target_profile["generator"]
        target_definition = TargetRegistry.builtins().get(generator_name)
        if target_definition is None:
            raise ValueError(f"No target registered for generator: {generator_name}")

        context.generation_contract = ContractDefinition().build(context.ir)
        ContractValidator().validate(context.generation_contract, target_definition)
        context.target_contract_mapping = TargetContractAdapter().map(
            context.generation_contract,
            target_definition,
        )

        OutputDirectory().prepare(context.output_dir, force=context.force_output)
        generator = TargetGeneratorFactory().create(
            target_definition,
            output_dir=context.output_dir,
            debug=context.debug,
        )

        generator.generate(context.ir)
        context.generated_components = generator.generated_components
        GeneratorArchitectureValidator().validate(
            context.generation_contract,
            target_definition,
            context.output_dir,
            context.generated_components,
        )

    def _ensure_no_diagnostic_errors(self, context) -> None:
        errors = context.architecture_report.get("errors", [])
        if not errors:
            return
        lines = [f"- {error['code']}: {error['message']}" for error in errors]
        raise GenerationBlockedError(
            "Generation blocked by architecture diagnostic errors:\n" + "\n".join(lines)
        )

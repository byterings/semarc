from architecture.contracts import (
    ContractDefinition,
    ContractValidator,
    GeneratorArchitectureValidator,
    TargetContractAdapter,
)
from generator.targets.factory import TargetGeneratorFactory
from generator.targets import TargetRegistry


class GenerationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("GenerationPass")
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

from generator.fastapi.fastapi_generator import FastApiGenerator
from generator.nestjs.nestjs_generator import NestJSGenerator
from generator.php_generator import PhpGenerator


class GenerationPass:
    def run(self, context) -> None:
        context.compiler_passes.append("GenerationPass")
        generator_name = context.target_profile["generator"]

        if generator_name == "php":
            generator = PhpGenerator(output_dir=context.output_dir, debug=context.debug)
        elif generator_name == "fastapi":
            generator = FastApiGenerator(output_dir=context.output_dir, debug=context.debug)
        elif generator_name == "nestjs":
            generator = NestJSGenerator(output_dir=context.output_dir, debug=context.debug)
        else:
            raise ValueError(f"No generator implemented for target: {context.target_profile['target']}")

        generator.generate(context.ir)
        context.generated_components = generator.generated_components

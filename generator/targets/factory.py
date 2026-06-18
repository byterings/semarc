from generator.fastapi.fastapi_generator import FastApiGenerator
from generator.nestjs.nestjs_generator import NestJSGenerator
from generator.php_generator import PhpGenerator


class TargetGeneratorFactory:
    """Creates target generators registered by target metadata."""

    GENERATORS = {
        "php": PhpGenerator,
        "fastapi": FastApiGenerator,
        "nestjs": NestJSGenerator,
    }

    def create(self, target_definition, output_dir: str, debug: bool = False):
        generator_class = self.GENERATORS.get(target_definition.generator)
        if generator_class is None:
            raise ValueError(f"No generator implemented for target: {target_definition.name}")
        return generator_class(output_dir=output_dir, debug=debug)

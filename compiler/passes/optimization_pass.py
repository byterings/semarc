from architecture.optimizer import ArchitectureOptimizer


class OptimizationPass:
    """Deterministic IR cleanup: ordering, de-duplication and migration sequencing."""

    def run(self, context) -> None:
        context.compiler_passes.append("OptimizationPass")
        context.ir = ArchitectureOptimizer().optimize(context.ir)

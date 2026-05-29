class OptimizationPass:
    """Placeholder compiler pass for deterministic IR cleanup."""

    def run(self, context) -> None:
        context.compiler_passes.append("OptimizationPass")
        context.ir["models"] = sorted(context.ir["models"], key=lambda model: model["name"])
        context.ir["repositories"] = sorted(context.ir["repositories"], key=lambda repo: repo["name"])
        context.ir["relationships"] = sorted(
            context.ir["relationships"],
            key=lambda relation: (relation["source"], relation["type"], relation["target"]),
        )

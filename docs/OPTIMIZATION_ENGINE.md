# Optimization Engine

`OptimizationPass` delegates to `ArchitectureOptimizer` (`semarc/architecture/optimizer.py`),
which cleans the Architecture IR deterministically before generation.

## Current Behaviour

- sorts models and repositories by name and relationships by source, type and target
- removes duplicate controllers, services and middlewares (by name) and duplicate validators
- orders migration tables topologically by foreign key, ties broken by table name, and
  assigns each table a `sequence`; a foreign key cycle is reported as an error

## Rules

An optimization may sort, de-duplicate and order. It must not change declared intent,
invent routes, remove declared models or alter relationship meaning.

## Possible Future Optimizations

- collapsing redundant dependency edges implied by stronger ones
- middleware ordering from the dependency graph
- warnings for routes that can never be reached because an earlier route shadows them

## Testing

`tests/ir/test_optimizer.py` checks ordering, independence from declaration order, cycle
detection and de-duplication.

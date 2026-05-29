# Optimization Engine

The optimization engine is responsible for deterministic cleanup of Architecture IR before generation.

Current optimization is intentionally small. The goal is correctness and deterministic output, not aggressive transformation.

## Current Behavior

`OptimizationPass` currently sorts:

- models
- repositories
- relationships

This ensures stable output across runs.

## Philosophy

Optimizations must preserve semantic meaning.

An optimization may:

- remove duplicate generated metadata
- simplify dependency order
- sort components
- remove unreachable target mappings

An optimization must not:

- change declared semantic intent
- invent new routes
- remove user-declared models
- alter relationship meaning

## Potential Optimizations

### Dead Route Removal

If route handlers are impossible to generate, a future pass could reject or remove them depending on compiler mode.

### Duplicate Validator Removal

Multiple validation declarations may map to the same validator component. The optimizer can deduplicate component entries while preserving field-level rules.

### Dependency Simplification

Redundant dependency edges can be collapsed if they are implied by stronger edges.

### Middleware Optimization

Middleware could be ordered based on dependency graph traversal.

### Migration Ordering

Migration tables can be ordered so referenced tables are created before dependent tables.

## Placement

```text
Architecture IR
    |
    v
OptimizationPass
    |
    v
Target Generator
```

Optimization happens after IR building and before generation.

## Testing

Every optimization should include deterministic tests:

- same input produces same output
- semantic meaning is preserved
- target outputs remain valid

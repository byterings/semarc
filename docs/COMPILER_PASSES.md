# Compiler Passes

SEMARC uses explicit compiler passes. Each pass accepts `CompilerContext`, mutates a focused part of compiler state, and leaves unrelated state alone.

## Pass Philosophy

Passes should be:

- isolated
- deterministic
- ordered
- easy to test
- free of target-specific side effects until generation

Each pass should have one responsibility.

## Compiler Context

`compiler/context.py` stores shared state:

- source path
- source text
- tokens
- AST
- relationship graph
- migration plan
- architecture diagnostics
- dependency graph
- architecture plan
- expanded architecture
- Architecture IR
- target profile
- generated artifacts
- compiler pass names

## Pass Order

```text
LexingPass
    |
ParsingPass
    |
ContractPass:AST
    |
ValidationPass
    |
RelationshipPass
    |
ConstraintPass
    |
ExpansionPass
    |
IRPass
    |
OptimizationPass
    |
ContractPass:IR
    |
GenerationPass
    |
DiagnosticReportPass
    |
ContractPass:Generation
```

## LexingPass

Responsibility: read source and tokenize it.

Input:

- `context.source_path`

Output:

- `context.source`
- `context.tokens`

Modification rules:

- must not create AST
- must not validate semantics
- must not generate code

## ParsingPass

Responsibility: parse tokens into AST.

Input:

- `context.tokens`

Output:

- `context.ast`

Modification rules:

- must not perform architecture expansion
- must not select target implementation strategy

## ValidationPass

Responsibility: validate semantic correctness.

Input:

- `context.ast`

Output:

- no output on success
- semantic error on failure

Checks include:

- missing project
- duplicate models
- duplicate routes
- unsupported database/auth/target
- undefined relationship models
- duplicate relationships
- circular ownership relationships

## ContractPass

Responsibility: enforce internal contracts between compiler layers.

Modes:

- `ContractPass:AST`
- `ContractPass:IR`
- `ContractPass:Generation`

Input:

- AST, IR, or generated component metadata

Output:

- no output on success
- contract error on malformed compiler state

Checks include:

- AST root structure
- required IR keys
- route handler shape
- repository metadata
- target-specific leakage markers
- generated component metadata shape

## RelationshipPass

Responsibility: build relationship graph and migration plan.

Input:

- AST models
- AST relations

Output:

- `context.relationship_graph`
- `context.relationship_plan`
- `context.migration_plan`

## ConstraintPass

Responsibility: run deterministic semantic architecture constraints before expansion.

Input:

- AST
- relationship plan

Output:

- `context.constraint_result`
- `context.architecture_report`

Checks include:

- conflicting authentication strategies
- JWT authentication without rate limiting
- missing database declarations
- route-level validation recommendations
- relationship depth and relationship integrity recommendations

Modification rules:

- must not generate code
- must not mutate AST semantics
- must not contain target-specific implementation logic

## ExpansionPass

Responsibility: select target profile and expand architecture.

Input:

- AST
- target override
- relationship plan

Output:

- `context.target_profile`
- `context.architecture_plan`
- `context.dependency_graph`
- `context.expanded_architecture`

## IRPass

Responsibility: build framework-independent Architecture IR.

Input:

- expanded architecture
- dependency graph
- relationship graph
- migration plan

Output:

- `context.ir`

## OptimizationPass

Responsibility: deterministic IR cleanup.

Current behavior:

- sort models
- sort repositories
- sort relationships

Future behavior may include:

- duplicate component removal
- dependency simplification
- unused route removal

## GenerationPass

Responsibility: select target generator and write files.

Input:

- `context.target_profile`
- `context.ir`

Output:

- generated backend files
- `context.generated_components`

Modification rules:

- this is the only pass that should write generated backend files
- it must not change semantic meaning

## DiagnosticReportPass

Responsibility: produce the final architecture diagnostics report after IR and generation metadata exist.

Input:

- AST
- relationship plan
- dependency graph
- Architecture IR

Output:

- `output/architecture_report.json`
- refreshed `context.architecture_report`

Modification rules:

- must not alter generated backend code
- must not change architecture decisions

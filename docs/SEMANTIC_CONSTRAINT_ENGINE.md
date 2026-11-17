# Semantic Constraint Engine

SEMARC uses a deterministic constraint engine to evaluate architecture quality before backend generation.

The constraint engine is not an AI system. It does not use LLMs, embeddings, natural language interpretation, or probabilistic scoring. Every diagnostic comes from an explicit rule registered in the compiler.

## Purpose

The compiler already transforms semantic intent into Architecture IR and target code. The constraint engine adds an analysis layer:

```text
Semantic AST
    |
    v
Relationship Plan
    |
    v
Constraint Engine
    |
    +-- errors
    +-- warnings
    +-- recommendations
    +-- architecture score
```

This lets SEMARC identify weak or conflicting architecture before generation.

## Location

```text
architecture/
└── constraints/
    ├── constraint_engine.py
    ├── constraint_registry.py
    ├── constraint_result.py
    └── rules/
        ├── auth_constraints.py
        ├── database_constraints.py
        ├── relationship_constraints.py
        ├── route_constraints.py
        └── architecture_constraints.py

compiler/
└── diagnostics/
    └── diagnostic.py
```

## Execution Order

The main constraint pass runs before architecture expansion:

```text
LexingPass
ParsingPass
ValidationPass
RelationshipPass
ConstraintPass
ExpansionPass
IRPass
OptimizationPass
GenerationPass
DiagnosticReportPass
```

`ConstraintPass` evaluates source-level architecture decisions. `DiagnosticReportPass` refreshes diagnostics after IR and dependency graph metadata exist, then writes the JSON report.

The full pass order is listed in `COMPILER_PASSES.md`. Warnings and recommendations never
stop compilation; diagnostic **errors** (for example `AUTH002`) block `GenerationPass`
before any file is written.

## Diagnostic Model

Diagnostics are structured records:

```json
{
  "type": "warning",
  "code": "AUTH001",
  "message": "JWT authentication endpoints should use rate limiting.",
  "severity": "warning",
  "source": "AUTH JWT"
}
```

Supported diagnostic classes:

- `DiagnosticError`
- `DiagnosticWarning`
- `DiagnosticRecommendation`

## Current Rules

Authentication rules:

- `AUTH001`: warns when JWT authentication is used without rate limiting.
- `AUTH002`: errors when multiple authentication strategies are declared.

Database rules:

- `DB001`: warns when no database declaration exists.
- `DB002`: recommends avoiding Redis cache for lightweight SQLite deployments.

Relationship rules:

- `REL001`: warns when relationship depth exceeds the prototype threshold.
- `REL002`: recommends repository-level tests for relationship-aware models.

Route rules:

- `ROUTE001`: recommends validation middleware for login routes without validation declarations.

Architecture rules:

- `ARCH001`: recommends completing token service support when repositories exist without authentication support.

## Architecture Score

The architecture score is deterministic. It starts at `100` and subtracts fixed weights:

- error: `30`
- warning: `5`
- recommendation: `2`

The score is bounded at `0`.

This score is intentionally simple. It is a compiler diagnostic signal, not a business quality metric.

## Report Output

After generation, SEMARC writes:

```text
output/architecture_report.json
```

Example:

```json
{
  "score": 91,
  "rules_executed": 7,
  "errors": [],
  "warnings": [],
  "recommendations": []
}
```

## Debug Output

Debug mode prints a compact constraint summary:

```bash
python3 main.py examples/blog_api.sem --debug
```

Example:

```text
[Constraint Engine]
Rules Executed: 7
Warnings: 1
Recommendations: 2
Errors: 0
Architecture Score: 91
```

## Extension Rules

Future constraint rules should:

- live under `architecture/constraints/rules/`
- emit structured diagnostics only
- remain target-independent unless explicitly checking target profile metadata
- avoid code generation
- avoid parser changes unless new semantic syntax has been formally added
- register through `ConstraintRegistry`

Constraint rules must not:

- parse free-form natural language
- call LLMs or external AI systems
- mutate generated code
- hide architecture decisions inside target generators

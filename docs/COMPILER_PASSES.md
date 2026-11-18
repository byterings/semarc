# Compiler Passes

SEMARC uses explicit compiler passes. Each pass accepts `CompilerContext`
(`compiler/context.py`), updates a focused part of the compiler state and leaves the rest
alone. Passes are deterministic, ordered and free of target-specific side effects until
generation.

## Pass Order

```text
LexingPass
ParsingPass
ContractPass:AST
ProfilePass
StdlibPass
ValidationPass
ModuleConstraintPass
RelationshipPass
ConstraintPass
ArchitectureAnalysisPass
ExpansionPass
IRPass
OptimizationPass
ContractPass:IR
GenerationPass
DiagnosticReportPass
ContractPass:Generation
```

`main.py` and `tests/support.py` run the passes in this order.

## LexingPass

Reads the source file and produces token lines. Keywords are matched case sensitively;
numbers, paths, types, relation types and HTTP methods get their own token types. It does
not build AST or validate semantics.

## ParsingPass

Builds the semantic AST through `ast/ast_builder.py`: models with field modifiers, routes
with optional access, validations with model scope and numeric parameters, relations,
profiles and packages. Reserved commands (`SERVICE`, `CONFIG`) raise a parser error.

## ContractPass

Checks compiler state between stages: AST structure, required IR keys, model, route and
repository shapes, target leakage in IR, and generated component metadata.

## ProfilePass and StdlibPass

Load `profiles/*.profile` and compose requested profiles with inheritance and cycle
detection, then discover `stdlib/**/module.yaml` modules into the module registry.

## ValidationPass

Rejects invalid programs before any architecture is built:

- missing project, unsupported database, auth or target (including `--target` overrides)
- naming rules, duplicate models and fields, declared implicit columns
- route syntax, duplicate routes and parameters, reserved routes, `PROTECTED` without auth
- relationship integrity, ownership cycles, fields that collide with foreign keys
- auth credential field types, `AUTH SESSION`
- `VALIDATE` targets, rule and type fit, `MIN`/`MAX` bounds, column and bcrypt limits
- duplicate stdlib module usage; then resolves module dependencies

## ModuleConstraintPass

Validates `requires` and `conflicts` of resolved stdlib modules (for example
`payment.razorpay` requires `database.mysql`).

## RelationshipPass

Builds the relationship graph, de-duplicated foreign keys (unique for `HAS_ONE`) and the
relationship-level migration plan.

## ConstraintPass and ArchitectureAnalysisPass

Run deterministic diagnostic rules (errors, warnings, recommendations, score) and the
read-only architecture analysis rules. Diagnostics never change the architecture, but
diagnostic **errors** block generation.

## ExpansionPass

Selects the target profile, runs `ResourcePlanner` and the architecture rule engine, and
expands the plan.

`ResourcePlanner` (`architecture/resource_planner.py`) decides the auth model and
credentials, final model specs with merged validation rules, references and dependents,
every route's operation, the default list routes, the auth routes and the access policy.
The rule engine builds the dependency graph from the same plan.

## IRPass

Builds the language-neutral Architecture IR from the expanded architecture, including
models, routes with operations and access, auth settings and migration tables, plus
dependency graph, relationship graph, module and profile metadata.

## OptimizationPass

Delegates to `ArchitectureOptimizer` (`architecture/optimizer.py`): sorts models,
repositories and relationships, removes duplicate components, and orders migration tables
topologically by foreign key with a sequence number.

## GenerationPass

1. Refuses to continue when diagnostics contain errors.
2. Resolves the target from `TargetRegistry` and builds the generation contract.
3. Validates target capabilities and layer wiring.
4. Prepares the output directory: clears a previous SEMARC output, refuses a foreign
   non-empty directory unless `--force` is given.
5. Runs the target generator.
6. Validates generated artifacts against the contract.

This is the only pass that writes project files.

## DiagnosticReportPass

Re-runs diagnostics with IR and dependency graph available and writes
`architecture_report.json` (score, findings, modules, profiles, statistics, contract
mapping) into the output directory.

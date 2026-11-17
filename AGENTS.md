# SEMARC Agent Guide

SEMARC is a Semantic Architecture Compiler.

This project is not:

- chatbot infrastructure
- LLM orchestration
- token prediction
- agent workflow automation

This project is:

- a deterministic semantic compiler
- an architecture synthesis engine
- a runnable project generator driven by strict semantic intent

## Architecture Philosophy

SEMARC compiles declarative architecture intent into runnable project foundations.

The compiler pipeline is:

```text
Semantic Source
-> Lexer
-> Parser
-> Semantic AST
-> Semantic Validator
-> Relationship Pass
-> Constraint Pass
-> Architecture Analysis
-> Resource Planning
-> Architecture Rule Engine
-> Dependency Graph Builder
-> Architecture Expansion
-> Architecture IR
-> Optimization Pass
-> Target Profile Selection
-> Generation Contract
-> Target Capability Validation
-> Target Generator
-> Generated Artifact Validation
-> Runnable Project
-> API Scenario Verification
```

Keep every stage isolated. Do not let parser logic leak into generators, and do not let generator syntax leak into AST nodes.

## Semantic Language Rules

The semantic language is strict, declarative, and deterministic.

Good:

```text
AUTH JWT
TARGET FASTAPI
RELATION User HAS_MANY Post
VALIDATE email REQUIRED EMAIL
PROFILE Ecommerce
USE payment.razorpay
```

Bad:

```text
Enable users to log in with secure tokens
```

Do not add natural language parsing.

## AST Rules

AST nodes represent semantic meaning only:

- project
- target
- database
- auth
- models
- fields
- routes
- relations
- validations

AST nodes must not contain PHP, Python, framework imports, file paths, templates, or generated strings.

## Architecture Rules

Architecture synthesis belongs in `architecture/`.

- `resource_planner.py` decides route operations, access policy, the auth model, field rules, references and dependents.
- `rules_engine.py` coordinates architecture rules.
- `rules/` contains domain-specific rules.
- `dependency_graph.py` tracks component dependencies.
- `relationship_engine.py` builds relationship graphs, foreign keys, and migration plans.
- `constraints/` evaluates deterministic architecture diagnostics and scoring.
- `profiles/` loads and composes profiles (with inheritance) into module selections.
- `packages/` loads package metadata (metadata only; no generation effect).
- `stdlib/` loads module definitions for `USE` and resolves their `depends`, `requires` and `conflicts`.
- `strategy_engine.py` selects implementation strategy and target profile.
- `expander.py` expands semantic plans before IR generation.
- `ir_builder.py` produces language-neutral IR.
- `optimizer.py` orders migrations by foreign keys and de-duplicates components.
- `contracts/` defines the generation contract, target capability validation, target mappings, and generated artifact validation.

Relationship and migration metadata must stay language-neutral in IR. Target generators map that metadata to migrations (PHP table definitions, Alembic revisions, TypeORM migrations). Do not generate runtime relationship helper methods until the target implements the underlying relationship runtime.

Rules must be deterministic and centralized.

Constraint rules may emit errors, warnings, and recommendations. They must be explicit rule checks, not AI-generated suggestions.

Future business capabilities should live in packages, profiles, or stdlib metadata instead of new core language keywords.

## Generator Boundaries

Generators consume Architecture IR after the Generation Contract has validated architecture wiring. They do not parse semantic source and do not make semantic decisions.

For model-backed routes, generated targets must preserve this dependency chain:

```text
API -> Business -> Persistence -> Entity
```

Do not generate fake security implementations: no demo tokens, permissive guards or unsigned tokens. `AUTH JWT` generates real HS256 tokens and bcrypt password hashing in every target; keep it that way.

Generators translate the IR only. Route operations, access policy, ownership, field rules and migration order are decided in `architecture/resource_planner.py` and the optimizer, never in a generator.

All targets must expose the same behaviour (`docs/GENERATED_API.md`) and ship a runner for the generated `api_scenario.json`.

SEMARC Core is the architecture engine. Target generators are runnable project builders. Future target work should focus on project templates and target packages, not lexer/parser/compiler expansion.

Target generators live under:

- `generator/php/`
- `generator/fastapi/`
- `generator/nestjs/`
- `generator/targets/`

Templates live under:

- `templates/php/`
- `templates/fastapi/`
- `templates/nestjs/`

Project template foundations live under:

- `generator/php/project_template/`
- `generator/fastapi/project_template/`
- `generator/nestjs/project_template/`

Every generated target should expose `/`, `/health`, and `/routes` and should use `generator/utils/inflector.py` for resource names. Shared target-neutral helpers live in `generator/utils/` (resource views, API scenario, project runtime files, template engine).

Keep generated projects readable, runnable, and prototype-friendly.

## Coding Conventions

- Prefer small classes with clear responsibility.
- Preserve current working behavior when extending features.
- Keep default target behavior as PHP unless semantic input says otherwise.
- Add validation before generation when new semantic constructs are introduced.
- Run `python3 scripts/validate_release.py` before committing. When generator output changes, run `python3 scripts/update_goldens.py`, review the diff, and verify runtime behaviour with `python3 scripts/e2e_runtime.py` (Docker).
- Pin exact dependency versions in generated projects.
- Commit messages and pull request descriptions must not contain AI tool names, attribution trailers or AI-related notes.
- Keep target-specific code inside target generators or templates.

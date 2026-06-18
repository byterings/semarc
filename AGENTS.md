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

- `rules_engine.py` coordinates architecture rules.
- `rules/` contains domain-specific rules.
- `dependency_graph.py` tracks component dependencies.
- `relationship_engine.py` builds relationship graphs, foreign keys, and migration plans.
- `constraints/` evaluates deterministic architecture diagnostics and scoring.
- `profiles/` loads future profile metadata without changing current generation.
- `packages/` loads future package metadata without changing current generation.
- `stdlib/` loads metadata-only module definitions for `USE` validation.
- `strategy_engine.py` selects implementation strategy and target profile.
- `expander.py` expands semantic plans before IR generation.
- `ir_builder.py` produces language-neutral IR.
- `contracts/` defines the generation contract, target capability validation, target mappings, and generated artifact validation.

Relationship and migration metadata must stay language-neutral in IR. PHP and FastAPI generators may map that metadata to SQL files, migration classes, and table definitions. Do not generate runtime relationship helper methods until the target implements the underlying relationship runtime.

Rules must be deterministic and centralized.

Constraint rules may emit errors, warnings, and recommendations. They must be explicit rule checks, not AI-generated suggestions.

Future business capabilities should live in packages, profiles, or stdlib metadata instead of new core language keywords.

## Generator Boundaries

Generators consume Architecture IR after the Generation Contract has validated architecture wiring. They do not parse semantic source and do not make semantic decisions.

For model-backed routes, generated targets must preserve this dependency chain:

```text
API -> Business -> Persistence -> Entity
```

Do not generate fake security implementations. Auth output should be honest scaffolding or TODO contracts unless a future target/package explicitly implements real security.

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

Every generated target should expose `/`, `/health`, and `/routes` and should use `generator/utils/inflector.py` for resource names.

Keep generated projects readable, runnable, and prototype-friendly.

## Coding Conventions

- Prefer small classes with clear responsibility.
- Preserve current working behavior when extending features.
- Keep default target behavior as PHP unless semantic input says otherwise.
- Add validation before generation when new semantic constructs are introduced.
- Keep target-specific code inside target generators or templates.

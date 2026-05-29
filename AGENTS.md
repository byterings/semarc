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
- a backend generator driven by strict semantic intent

## Architecture Philosophy

SEMARC compiles declarative architecture intent into backend structure and implementation code.

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
-> Target Generator
-> Generated Backend
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
- `strategy_engine.py` selects implementation strategy and target profile.
- `expander.py` expands semantic plans before IR generation.
- `ir_builder.py` produces language-neutral IR.

Relationship and migration metadata must stay language-neutral in IR. PHP and FastAPI generators may map that metadata to SQL files, migration classes, SQLAlchemy tables, or ORM relationship methods.

Rules must be deterministic and centralized.

Constraint rules may emit errors, warnings, and recommendations. They must be explicit rule checks, not AI-generated suggestions.

## Generator Boundaries

Generators consume Architecture IR. They do not parse semantic source and do not make semantic decisions.

Target generators live under:

- `generator/php/`
- `generator/fastapi/`

Templates live under:

- `templates/php/`
- `templates/fastapi/`

Keep generated code readable and prototype-friendly.

## Coding Conventions

- Prefer small classes with clear responsibility.
- Preserve current working behavior when extending features.
- Keep default target behavior as PHP unless semantic input says otherwise.
- Add validation before generation when new semantic constructs are introduced.
- Keep target-specific code inside target generators or templates.

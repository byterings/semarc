# System Architecture

SEMARC is a deterministic semantic compiler for backend architecture. It converts strict architecture intent into target-specific backend code through explicit compiler stages.

SEMARC is not chatbot infrastructure, LLM orchestration, token prediction, or a probabilistic code generator. It is a semantic compiler and architecture synthesis engine.

## Philosophy

Traditional programming describes how a system executes. SEMARC describes what architecture should exist.

Example:

```text
AUTH JWT
DATABASE MYSQL
MODEL User
ROUTE POST /login
```

The compiler expands this into architecture components, dependency metadata, migrations, and target-specific backend files.

## Pipeline

```text
Semantic Source
    |
    v
Lexer
    |
    v
Parser
    |
    v
Semantic AST
    |
    v
Semantic Validation
    |
    v
Relationship Engine
    |
    v
Constraint Engine + Diagnostics
    |
    v
Architecture Rule Engine + Dependency Graph
    |
    v
Architecture Expansion
    |
    v
Architecture IR
    |
    v
Optimization Passes
    |
    v
Target Generator
    |
    v
Runnable Project
```

## Layer Responsibilities

### Semantic Source

Purpose: user-authored architecture intent.

Input: `.sem` file.

Output: raw text.

Boundary: source must remain strict and declarative. It must not contain framework code or natural language instructions.

### Lexer

Purpose: split source into deterministic tokens.

Input: source text.

Output: token lines.

Boundary: lexer classifies tokens only. It must not infer architecture, validate model existence, or generate code.

### Parser

Purpose: convert token lines into semantic AST nodes.

Input: token lines.

Output: `ArchitectureNode`.

Boundary: parser handles grammar only. It must not decide implementation strategy or target-specific structure.

### Semantic AST

Purpose: preserve semantic architecture meaning.

Input: parser output.

Output: language-independent tree of semantic nodes.

Boundary: AST contains no PHP, Python, SQL, FastAPI, or folder layout.

### Semantic Validation

Purpose: detect invalid semantic programs.

Input: AST.

Output: valid AST or readable semantic errors.

Boundary: validation rejects invalid architecture meaning; it does not synthesize new components.

### Relationship Engine

Purpose: convert semantic relationships into relationship graph, foreign keys, and migration metadata.

Input: AST relations and models.

Output: relationship plan and migration plan.

Boundary: this layer remains target-neutral.

### Constraint Engine

Purpose: evaluate semantic architecture quality before generation.

Input: AST, relationship plan, dependency graph, and IR where available.

Output: deterministic errors, warnings, recommendations, and architecture score.

Boundary: constraints diagnose architecture decisions. They do not parse natural language, invent new syntax, or render target code.

### Dependency Graph

Purpose: track architecture component dependencies.

Input: architecture rule output.

Output: graph nodes, dependency edges, traversal order.

Boundary: dependency graph describes architecture dependencies, not import statements.

### Resource Planning

Purpose: decide what the generated API does.

Input: AST, foreign keys from the relationship engine.

Output: auth settings, final model specs (fields, rules, references, dependents) and one
operation plus access policy per route (`semarc/architecture/resource_planner.py`).

Boundary: decisions are target-neutral; generators only translate them.

### Architecture Expansion

Purpose: expand compact semantic intent into component plans.

Input: AST, rule engine output, target profile, relationship plan.

Output: expanded architecture dictionary.

Boundary: expansion may choose components such as `TokenService`, but it does not render files.

### Architecture IR

Purpose: create framework-independent implementation representation.

Input: expanded architecture.

Output: IR dictionary with models, routes, services, repositories, relationships, migrations, and dependency metadata.

Boundary: IR is target-neutral. It should not contain PHP method bodies or Python imports.

### Optimization Passes

Purpose: deterministic cleanup and ordering of IR.

Input: IR.

Output: optimized IR.

Boundary: optimizations must preserve semantic meaning.

### Target Generators

Purpose: map IR to a runnable project.

Input: Architecture IR, after the generation contract has been validated.

Output: a project directory (default `output/`, configurable with `--output`).

Boundary: generators do not parse source and do not invent architecture rules.

## Component Interaction

```text
semarc/compiler/context.py
    stores source, tokens, AST, relationship plan, graph, IR, target profile

semarc/compiler/passes/*
    mutate CompilerContext one stage at a time

semarc/architecture/*
    owns synthesis, relationship planning, dependency modeling, IR building

semarc/generator/*
    owns target mapping and templates
```

## Current Targets

```text
Architecture IR
    |
    +-- PHP Generator      -> PHP 8.1+ API (PDO, JWT, migrations, tests/run.php)
    +-- FastAPI Generator  -> FastAPI + SQLAlchemy 2 + Alembic API (pytest)
    +-- NestJS Generator   -> NestJS 11 + TypeORM API (jest)
```

Every target produces the same API behaviour (see `GENERATED_API.md`), supports MySQL,
PostgreSQL and SQLite, and ships Docker configuration and a test runner for the generated
`api_scenario.json`.

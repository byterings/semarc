# Architecture Intelligence

Architecture Intelligence is the deterministic architecture analysis system introduced in SEMARC v0.9.0.

Its purpose is to inspect an already valid semantic architecture and report architecture-quality findings before backend generation.

Architecture Intelligence is:

- rule-based
- deterministic
- compiler-oriented
- read-only

Architecture Intelligence is not:

- AI
- machine learning
- probabilistic inference
- natural language reasoning
- automatic architecture rewriting

It does not modify the semantic source, the semantic AST, the Architecture IR, or generator output. It only analyzes the resolved architecture state and produces findings.

# Philosophy

Traditional compilers answer:

```text
Is this valid?
```

SEMARC already answers that question through semantic validation, constraint validation, dependency validation, and compiler contracts.

Architecture Intelligence adds a second question:

```text
Is this architecture reasonable?
```

This layer exists because a system can be syntactically valid and semantically valid while still being weak from an architecture perspective.

Examples:

- public routes may exist without any authentication strategy
- payment capabilities may be present without audit support
- models may be declared but never used
- profile and infrastructure choices may be mismatched

Architecture Intelligence helps surface these issues early, while keeping SEMARC deterministic and compiler-like.

# Analysis Pipeline

Architecture Intelligence runs in the main compilation pipeline after validation and before generation.

```text
PROFILE
-> Profile Composition
-> Module Resolution
-> Dependency Resolution
-> Constraint Validation
-> Architecture Analysis
-> IR
-> Generators
```

In compiler terms, the flow is:

```text
Semantic Source
-> Lexer
-> Parser
-> Semantic AST
-> Profile Pass
-> Stdlib Pass
-> Validation Pass
-> Module Constraint Pass
-> Relationship Pass
-> Constraint Pass
-> Architecture Analysis Pass
-> Expansion Pass
-> IR Pass
-> Generation Pass
```

This ordering matters:

- validation runs first so analysis sees a coherent architecture
- profile composition and module resolution run first so analysis can inspect resolved modules
- generation runs later so analysis stays independent from target-specific code

# Severity Levels

Architecture Intelligence currently emits two non-blocking severity levels.

## Warnings

Warnings indicate potential architectural problems.

A warning means:

- the system can still compile
- the architecture may be incomplete, weak, or inconsistent
- the finding deserves review

Warnings are intended for issues that look structurally suspicious.

## Recommendations

Recommendations indicate suggested improvements.

A recommendation means:

- the system can still compile
- the architecture is allowed
- a stronger or more appropriate architecture choice may exist

Recommendations are advisory, not corrective.

Neither warnings nor recommendations stop compilation.

# Current Rules

## SEM9001

### Public route without authentication

**Purpose**

Detect routes that appear public when no authentication system is configured.

**Detection logic**

This rule triggers when:

- at least one non-auth route exists
- no semantic `AUTH` declaration is present
- no resolved stdlib module begins with `auth.`

Auth-only routes such as `/login` are not treated as public resource routes for this rule.

**Example**

```text
PROJECT PublicApi

DATABASE MYSQL

MODEL Post
    title STRING

ROUTE GET /posts
```

**Example warning output**

```text
SEM9001 Public route detected without authentication: GET /posts
```

## SEM9002

### Payment module without audit logging

**Purpose**

Identify payment-related module usage without audit coverage.

**Detection logic**

This rule triggers when:

- a resolved module name starts with `payment.`
- `audit.standard` is not present in the resolved module set

This rule evaluates the fully resolved module graph, not only direct `USE` declarations.

**Example**

```text
PROJECT Shop

DATABASE MYSQL

USE payment.demo

MODEL User
    email STRING

ROUTE GET /orders
```

**Example recommendation output**

```text
SEM9002 Payment module loaded without audit logging: payment.demo
```

## SEM9003

### Model appears unused

**Purpose**

Detect domain models that are declared but not meaningfully referenced by routes, relationships, or authentication.

**Detection logic**

This rule triggers when a model:

- is not part of any declared relationship
- is not the implicit auth model used by semantic authentication handling
- is not referenced by route path segments using simple singular or plural matching

Examples of route matching:

- `User` matches `/user` and `/users`
- `BlogPost` matches `/blog_post` and `/blog_posts`

This is intentionally heuristic but deterministic.

**Example**

```text
PROJECT UnusedModel

DATABASE MYSQL

MODEL User
    email STRING

MODEL Comment
    body STRING

ROUTE GET /users
```

**Example warning output**

```text
SEM9003 Model appears unused: Comment
```

## SEM9004

### Ecommerce profile using SQLite

**Purpose**

Flag lightweight database selection for an ecommerce-oriented profile.

**Detection logic**

This rule triggers when:

- the resolved profile set includes `Ecommerce`
- the semantic database is `SQLITE`

The rule is advisory. It does not declare SQLite invalid.

**Example**

```text
PROJECT Shop

PROFILE ECOMMERCE

DATABASE SQLITE

MODEL User
    email STRING

ROUTE GET /users
```

**Example recommendation output**

```text
SEM9004 Ecommerce profile is using SQLITE; MYSQL is a stronger default for commerce workloads.
```

## SEM9005

### Authentication loaded but no protected routes detected

**Purpose**

Detect authentication setup that appears to exist without any non-auth route to protect.

**Detection logic**

This rule triggers when:

- semantic `AUTH` is present, or a resolved module begins with `auth.`
- all declared routes are auth-only routes such as `/login`

This helps identify architectures where authentication was enabled but no protected API surface was actually declared.

**Example**

```text
PROJECT AuthOnly

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING

ROUTE POST /login
```

**Example recommendation output**

```text
SEM9005 Authentication is configured but no protected routes were detected.
```

# Example Analysis Report

Example semantic source:

```text
PROJECT Shop

PROFILE ECOMMERCE

DATABASE SQLITE

MODEL User
    email STRING

MODEL Comment
    body STRING

ROUTE GET /users
```

Possible analysis findings:

- `SEM9001` because `/users` is public and no authentication is configured
- `SEM9003` because `Comment` is unused
- `SEM9004` because the `Ecommerce` profile is paired with `SQLITE`

Example `architecture_analysis` section in `output/architecture_report.json`:

```json
{
  "architecture_analysis": {
    "rules_executed": 5,
    "warnings": [
      {
        "type": "warning",
        "code": "SEM9001",
        "message": "Public route detected without authentication: GET /users",
        "severity": "warning",
        "source": "route:GET /users"
      },
      {
        "type": "warning",
        "code": "SEM9003",
        "message": "Model appears unused: Comment",
        "severity": "warning",
        "source": "model:Comment"
      }
    ],
    "recommendations": [
      {
        "type": "recommendation",
        "code": "SEM9004",
        "message": "Ecommerce profile is using SQLITE; MYSQL is a stronger default for commerce workloads.",
        "severity": "info",
        "source": "profile:Ecommerce"
      }
    ]
  }
}
```

# Design Principles

Architecture Intelligence follows a strict set of design principles.

## Deterministic

The same semantic input must always produce the same analysis findings.

There is no randomness, no model inference, and no external service dependency.

## Repeatable

Analysis must be stable across environments and across repeated compiler runs.

## Read-only

Analysis must never modify:

- semantic source
- AST nodes
- dependency graph meaning
- expanded architecture
- Architecture IR
- generated code

## No automatic architecture modification

Architecture Intelligence reports issues. It does not silently fix them.

## No hidden behavior

Every finding must come from an explicit rule in the analysis system.

## No runtime learning

There is no training, adaptive behavior, or evolving model state.

# Adding New Rules

New rules should be added through the analysis subsystem, not by scattering warnings across unrelated compiler layers.

Relevant components:

- `ArchitectureRule`
- `ArchitectureAnalyzer`
- `ArchitectureAnalysisResult`
- `ArchitectureAnalysisPass`

## Rule model

`ArchitectureRule` contains:

- rule id
- severity
- title
- message
- evaluator function

## Analysis engine

`ArchitectureAnalyzer`:

- constructs the analysis context
- executes rules in deterministic order
- records warnings and recommendations

## Result object

`ArchitectureAnalysisResult` stores:

- warnings
- recommendations
- rules executed count

## Compiler pass

`ArchitectureAnalysisPass`:

- runs after validation-related passes
- stores analysis output in compiler context
- does not mutate the architecture

## Suggested process for adding a new rule

1. Define the architecture smell or recommendation clearly.
2. Decide whether the result should be a warning or a recommendation.
3. Add an evaluator in `semarc/architecture/analysis/analyzer.py` or move rule logic into a dedicated rule module if the set grows.
4. Register the rule in the analyzer’s default rule list.
5. Keep the rule deterministic and target-independent.
6. Add unit tests for:
   - positive detection
   - false-positive avoidance
   - interaction with existing profiles or modules when relevant
7. Verify the rule appears correctly in `architecture_report.json`.

New rules should inspect semantic architecture state, not generated framework code.

# Future Direction

Architecture Intelligence is intended to grow carefully.

Likely future analysis areas include:

- security analysis
- scalability analysis
- observability analysis
- performance analysis
- architecture consistency analysis

Examples of future deterministic checks:

- missing rate limiting around auth endpoints
- write-heavy workloads without caching strategy
- public data mutation routes without validation layers
- relationship graphs with excessive ownership depth
- route sets that imply missing repository or service structure

Future intelligence must remain:

- rule-based
- deterministic
- local
- compiler-oriented

It must not become an opaque or probabilistic subsystem.

# Non-Goals

Architecture Intelligence does not include:

- machine learning
- LLMs
- AI agents
- code generation decisions
- automatic architecture rewrites
- remote services
- telemetry
- cloud dependencies

It is not a recommendation engine driven by user behavior or external data.

# Summary

Architecture Intelligence extends SEMARC from a compiler that validates semantic intent into a compiler that also evaluates architecture quality.

It does this with explicit rules, deterministic execution, and read-only diagnostics.

The result is a stronger compiler pipeline:

```text
valid architecture
plus
architecture quality feedback
```

This keeps SEMARC aligned with its core philosophy: strict semantic intent, deterministic compilation, and clean architectural boundaries.

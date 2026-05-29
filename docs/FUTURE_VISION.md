# Future Vision

SEMARC's long-term goal is semantic systems engineering: describing architecture intent once and compiling it into deterministic system artifacts.

Current focus remains backend compilation.

## Current Scope

SEMARC currently targets:

- semantic backend architecture
- models
- routes
- auth
- validation
- relationships
- migrations
- PHP output
- FastAPI output

## Long-Term Direction

SEMARC may eventually support:

- frontend generation
- infrastructure synthesis
- workflow systems
- semantic deployment
- semantic automation
- policy generation
- observability scaffolding

These are future directions, not current commitments.

## Semantic Backend Compiler

Near-term work should strengthen:

- Architecture IR
- relationship modeling
- migration correctness
- target profiles
- target generator parity
- optimization passes
- standard library modules

## Frontend Generation

A future frontend target could compile:

```text
PAGE Dashboard
FORM Login
RESOURCE User
```

into UI routes, forms, validation, and API clients.

This should not happen until backend semantics are stable.

## Infrastructure Synthesis

Future infrastructure output could include:

- Docker files
- environment files
- deployment manifests
- database provisioning
- queue workers

Infrastructure synthesis should consume Architecture IR, not semantic source directly.

## Workflow Systems

SEMARC could eventually describe workflows:

```text
WORKFLOW PublishPost
    REQUIRE Auth
    UPDATE Post.status
    EMIT PostPublished
```

This would require a workflow IR and deterministic execution model.

## Semantic Deployment

Semantic deployment could define:

```text
DEPLOY Docker
DATABASE ManagedPostgres
CACHE Redis
```

This must remain deterministic and explicit.

## What SEMARC Should Avoid

SEMARC should not become:

- a chatbot wrapper
- a prompt orchestration system
- a probabilistic code generator
- a hidden decision engine

All compiler decisions should be explainable through rules, passes, IR, profiles, and templates.

## Guiding Principle

SEMARC should make architecture intent precise enough to compile.

```text
Semantic Intent
    |
    v
Architecture Plan
    |
    v
Architecture IR
    |
    v
Target Artifacts
```

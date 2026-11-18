# Generation Contract

SEMARC's Generation Contract Foundation defines how Architecture IR becomes a coherent generated project.

The contract is not a framework feature. It is a framework-neutral consistency layer that every target renderer must satisfy before and after generation.

## Purpose

Generators previously emitted files independently:

```text
routes
controllers
services
repositories
models
```

That made it possible to generate dead layers, duplicated structure, and routes that bypassed the generated architecture.

The Generation Contract establishes one architecture definition that every target maps into its own framework conventions.

```text
Architecture IR
    |
Generation Contract
    |
Target Capability Validation
    |
Target Renderer
    |
Generated Artifact Validation
```

## Architecture Layers

The core contract uses framework-neutral layers:

- Project Layer
- Configuration Layer
- Entity Layer
- Persistence Layer
- Business Layer
- API Layer
- Auth Layer

These are architecture concepts, not implementation names.

The core contract does not define controller, router, repository, handler, guard, or dependency-injection layers. Those are target-specific mappings.

## Layer Dependency Model

For model-backed endpoints, generated architecture must follow this dependency shape:

```text
API Layer
    |
Business Layer
    |
Persistence Layer
    |
Entity Layer
```

Example semantic source:

```text
PROJECT CRM

DATABASE MYSQL

MODEL Customer
    name STRING

ROUTE GET /customers
```

Contract components:

```json
{
  "components": [
    {"id": "entity:Customer", "layer": "entity"},
    {"id": "persistence:CustomerRepository", "layer": "persistence"},
    {"id": "business:CustomerService", "layer": "business"},
    {"id": "api:GET:/customers", "layer": "api"}
  ],
  "dependencies": [
    {"source": "persistence:CustomerRepository", "target": "entity:Customer"},
    {"source": "business:CustomerService", "target": "persistence:CustomerRepository"},
    {"source": "api:GET:/customers", "target": "business:CustomerService"}
  ]
}
```

## Target Mapping

Each target maps neutral layers to framework concepts.

PHP:

```text
Entity Layer        -> models
Persistence Layer   -> repositories
Business Layer      -> services
API Layer           -> controllers + routes
Auth Layer          -> auth services + middleware
```

FastAPI:

```text
Entity Layer        -> models + schemas
Persistence Layer   -> repositories
Business Layer      -> services
API Layer           -> routers
Auth Layer          -> auth dependencies + middleware
```

NestJS:

```text
Entity Layer        -> model/entity classes
Persistence Layer   -> repositories
Business Layer      -> services
API Layer           -> controllers
Auth Layer          -> guards + auth module
```

## Target Capabilities

Targets declare support for contract layers through `TargetCapability`.

Current capabilities:

- `supports_project_layer`
- `supports_configuration_layer`
- `supports_entity_layer`
- `supports_persistence_layer`
- `supports_business_layer`
- `supports_api_layer`
- `supports_auth_layer`

Generation fails before files are written if the selected target does not support a required contract layer.

## Contract Validation

`ContractValidator` validates the neutral contract before generation.

Checks include:

- target supports all required layers
- dependency targets exist
- API components reference business components for model-backed routes
- business components reference persistence components
- persistence components reference entity components
- duplicate API routes are rejected

API components are built from the IR route operations. Auth operations depend on the auth
layer; protected routes also depend on it. Custom operations (routes that match no
resource shape) are marked `todo` and generate explicit 501 responses instead of business wiring.

## Artifact Validation

`GeneratorArchitectureValidator` runs after target rendering.

Checks include:

- duplicate output paths
- missing required artifacts for contract-backed layers
- duplicate generated architecture trees
- broken PHP `require_once` paths

This prevents generated files from drifting away from the contract.

## Runtime Behaviour

Since v0.14.0 the generated layers are fully implemented: repositories persist to MySQL,
PostgreSQL or SQLite, authentication issues and verifies HS256 JWTs with bcrypt password
hashing, and services enforce validation, uniqueness, reference integrity, ownership and
safe deletes. The observable behaviour is specified in `GENERATED_API.md`.

The structural contract (this document) guarantees the wiring; the behavioural contract is
verified by `api_scenario.json`, which every target ships with a runner and which
`scripts/e2e_runtime.py` replays against live Docker stacks.

SEMARC still does not generate fake security: no demo tokens, no permissive guards, no
unsigned tokens. Generated projects refuse to sign tokens with a `JWT_SECRET` shorter than 32
characters.

Out of scope for the contract: roles and permissions, rate limiting, framework downloads at
generation time and regeneration into modified projects.

## Target Development Guide

To add or harden a target:

1. Add or update its `TargetDefinition`.
2. Declare layer support with `TargetCapability`.
3. Map neutral layers in `TargetContractAdapter`.
4. Render files from Architecture IR according to the contract.
5. Add target compliance tests under `tests/target_compliance/`.
6. Ensure generated artifacts pass `GeneratorArchitectureValidator`.
7. Ship a runner for `api_scenario.json` and make `scripts/e2e_runtime.py` pass for every database.

New targets should not add parser logic or semantic keywords. Target-specific structure belongs in the target renderer and templates.

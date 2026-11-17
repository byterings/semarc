# Package System Design

SEMARC packages are the planned extension point for reusable semantic modules.

The goal is to prevent keyword expansion in the core language. Features such as
payments, reporting, notifications, search, storage, caching, and auditing
should become packages instead of new top-level language constructs.

Current status: package metadata (`stdlib/*/package.meta`) is loaded for reporting. Module
behaviour lives in the stdlib module system (`module.yaml`, see `STDLIB_MODULE_SYSTEM.md`),
which resolves dependencies and constraints. Neither changes generated code yet.

## Philosophy

Core language primitives should stay small:

```text
PROJECT
TARGET
DATABASE
MODEL
RELATION
ROUTE
SERVICE
AUTH
CONFIG
PROFILE
USE
```

Future capabilities should use package references:

```text
USE payment.razorpay
USE notification.email
USE search.indexing
```

These declarations should eventually load deterministic semantic modules.

## Directory Layout

```text
stdlib/
├── auth/
├── database/
├── reporting/
├── payment/
├── notification/
├── search/
├── storage/
├── cache/
└── relationships/
```

Each package directory may contain metadata and, in future versions, semantic
rules, constraints, target mappings, compatibility metadata, and tests.

## Foundation Objects

```text
architecture/packages/
├── package.py
├── registry.py
└── loader.py
```

`Package` stores:

- name
- domain
- description
- dependencies
- metadata

`PackageRegistry` stores loaded packages by name.

`PackageLoader` reads `stdlib/*/package.meta` files.

## Loading Flow

Planned flow:

```text
USE payment.razorpay
    |
    v
PackageLoader
    |
    v
PackageRegistry
    |
    v
future package pass
    |
    v
architecture rules and constraints
```

The current loader stops at metadata registration.

## Package Dependencies

Packages may eventually require other packages:

```text
USE payment.razorpay
```

may require:

```text
notification.email
audit.standard
```

Dependency resolution should be deterministic:

1. Load requested package metadata.
2. Resolve declared dependencies.
3. Validate dependency cycles.
4. Add package architecture rules.
5. Add package constraints.
6. Expand into Architecture IR.

Package dependency rules must remain target-independent until generator mapping.

## Boundaries

Packages may define semantic architecture behavior in future versions.

Packages must not:

- parse natural language
- call AI systems
- generate code directly from AST
- mutate target generators
- introduce hidden framework assumptions into IR

Target-specific package output belongs in target generator mappings or templates.

## Roadmap

Near-term:

- metadata loading
- package registry contracts
- package dependency graph
- package compatibility checks

Later:

- payment modules
- notification modules
- search modules
- storage modules
- auditing modules
- package-provided constraints
- package-provided target mappings

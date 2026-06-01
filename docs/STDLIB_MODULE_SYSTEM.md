# Stdlib Module System

SEMARC stdlib modules are metadata-only semantic extension points.

Current version: v0.5.0 foundation.

The stdlib module system does not generate code, add business behavior, resolve
module dependencies, or alter target generators. It only discovers module
metadata and validates `USE` declarations.

## Purpose

Core language keywords should remain small. Future capabilities should be
represented as stdlib modules:

```text
USE auth.jwt
USE cache.redis
```

This avoids adding new top-level keywords for payments, reporting,
notifications, search, storage, cache, or auditing.

## Directory Structure

Modules are discovered recursively under `stdlib/` by looking for
`module.yaml` files.

```text
stdlib/
├── auth/
│   └── jwt/
│       └── module.yaml
└── cache/
    └── redis/
        └── module.yaml
```

The loader does not hardcode module names.

## module.yaml Schema

Required fields:

```yaml
name: auth.jwt
version: 1.0
description: JWT authentication module
```

Fields:

- `name`: semantic module name used by `USE`
- `version`: metadata version string
- `description`: human-readable module description

## Loader Flow

```text
StdlibPass
    |
    v
StdlibLoader
    |
    v
ModuleDefinition[]
    |
    v
ModuleRegistry
```

`StdlibPass` runs before semantic validation so `USE` declarations can be
validated against the module registry.

## USE Resolution

Example source:

```text
PROJECT Shop

TARGET FASTAPI

USE auth.jwt
USE cache.redis
```

Validation checks each `USE` name against `ModuleRegistry`.

If the module exists, compilation continues and the resolved modules are added
to the architecture report.

If the module does not exist, the `USE` declaration remains valid legacy
metadata. This preserves v0.4.0 compatibility for company-specific package
metadata:

```text
USE company.internal_standard
```

## Diagnostics

Stdlib diagnostics:

- `SEM5001`: reserved for unknown module diagnostics if strict module mode is introduced later
- `SEM5002`: duplicate module name discovered
- `SEM5002`: duplicate known module usage in source
- `SEM5003`: invalid `module.yaml`
- `SEM5004`: stdlib loading failure

## Architecture Report

Generated `output/architecture_report.json` includes resolved modules:

```json
{
  "modules": [
    {
      "name": "auth.jwt",
      "version": "1.0",
      "description": "JWT authentication module",
      "source_path": "stdlib/auth/jwt/module.yaml"
    }
  ]
}
```

## Non-Goals

The v0.5.0 foundation does not implement:

- module dependencies
- module constraints
- module inheritance
- module composition
- version resolution
- remote repositories
- package marketplace
- generator integration
- code generation from modules

# SEMARC Ownership Model

SEMARC v1 is designed to generate project foundations.

It compiles strict semantic architecture intent into backend structure, starter implementation code, migrations, reports, and target-specific project scaffolding.

SEMARC is not intended to permanently own the generated project after generation.

## Philosophy

SEMARC describes what the backend architecture should contain:

```text
PROJECT BlogAPI
DATABASE MYSQL
AUTH JWT
MODEL User
ROUTE GET /users
```

The compiler turns that semantic intent into a working foundation.

After generation, developers own the generated codebase.

## What SEMARC Generates

SEMARC may generate:

- project structure
- model classes
- controllers or routers
- services
- repositories
- middleware or guards
- validators
- migrations
- configuration files
- architecture reports
- target-specific scaffold files

The generated code is intentionally readable and direct so developers can inspect and modify it.

## What Developers Customize

Developers are expected to own:

- business logic
- production authentication behavior
- database connection details
- persistence strategy
- request and response contracts
- error handling
- deployment configuration
- observability
- performance tuning
- security hardening
- framework-specific conventions beyond the prototype scaffold

SEMARC provides the foundation. Developers turn it into the application.

## Why Regeneration Is Out of Scope for v1

Regenerating into an already customized codebase requires an ownership model for every generated region.

That introduces hard problems:

- preserving manual edits
- merging generated changes
- tracking protected code regions
- resolving template drift
- detecting user-owned files
- deciding when generated code should replace existing code

SEMARC v1 avoids those problems intentionally.

The v1 contract is:

```text
Semantic Architecture -> Generated Foundation
```

not:

```text
Semantic Architecture -> Perpetually Managed Application
```

## Practical Workflow

A recommended v1 workflow is:

1. Write semantic architecture intent.
2. Generate a backend foundation.
3. Review the architecture report.
4. Commit or copy the generated project into application development.
5. Let developers own future application changes.

Regeneration should be treated as creating a new foundation, not patching an existing production project.

## Future Possibilities

Future SEMARC versions may explore regeneration and merge workflows, but those require explicit design.

Potential future concepts include:

- protected code regions
- generated file manifests
- ownership metadata
- merge-safe templates
- migration-aware regeneration

These are not part of SEMARC v1.

## Summary

SEMARC generates deterministic backend foundations from semantic architecture intent.

Developers own the generated projects after generation.

This boundary keeps SEMARC focused, predictable, and compiler-oriented while avoiding unsafe assumptions about user-modified application code.

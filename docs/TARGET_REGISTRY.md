# Target Registry

SEMARC v0.13.0 introduced a metadata-driven target registry. Targets are described by local
manifests and registered before generation. The implemented targets are:

- PHP
- FastAPI
- NestJS

Targets without a manifest and generator (for example Laravel or Node) are rejected during
validation. No framework downloads, marketplace, version resolution or remote target
loading exist yet.

## Target Manifest

Each built-in target has a manifest:

```text
generator/<target>/project_template/target.yaml
```

Example:

```yaml
name: php
language: PHP
description: Runnable core PHP project generator
generator: php
supports:
  - project
  - configuration
  - entity
  - persistence
  - business
  - api
  - auth
```

## TargetDefinition

`TargetDefinition` is the registered target model.

Fields:

- `name`
- `language`
- `description`
- `generator`
- `metadata`
- `capabilities`

## TargetMetadata

`TargetMetadata` is loaded from `target.yaml`.

It records:

- target name
- language
- description
- generator key
- declared support list
- source path

## TargetCapability

`TargetCapability` declares which generation contract layers a target supports:

- project
- configuration
- entity
- persistence
- business
- api
- auth

Generation validates capabilities before writing files.

## Registry Flow

```text
TARGET PHP
    |
TargetRegistry
    |
TargetDefinition
    |
Generation Contract Validation
    |
TargetGeneratorFactory
    |
Target Generator
```

`TargetRegistry.builtins()` discovers built-in target manifests deterministically.

## Future Target Integration

To add a future target:

1. Create `generator/<target>/project_template/target.yaml`.
2. Declare target capabilities.
3. Implement the target generator.
4. Register the generator class in `TargetGeneratorFactory`.
5. Add target compliance tests.
6. Ensure generated output satisfies the Generation Contract.
7. Ship a runner for `api_scenario.json` and pass `scripts/e2e_runtime.py` on every database.

New targets must not require parser, AST, or semantic language changes.

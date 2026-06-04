# Project Template System

SEMARC v0.12.0 introduces the Project Template Foundation.

This changes the target generator direction from:

```text
Architecture IR -> generated code files
```

to:

```text
Architecture IR -> runnable project foundation
```

The compiler core remains stable. Project templates live in the generator layer.

## SEMARC Core

SEMARC Core is the architecture engine.

It owns:

- lexical analysis
- parsing
- semantic AST construction
- semantic validation
- profile composition
- stdlib module resolution
- module dependency resolution
- module constraint validation
- relationship planning
- architecture intelligence
- Architecture IR generation

SEMARC Core does not own framework bootstrap files, Docker files, runtime package manifests, or target-specific project layout.

## Target System

Targets are runnable project builders.

Current built-in targets:

- `php`
- `fastapi`
- `nestjs`

Target metadata is represented by:

- `TargetDefinition`
- `TargetMetadata`
- `TargetRegistry`
- `TargetLoader`

The foundation exists so future target packages can be described with metadata before SEMARC supports installable target packages.

Example target metadata:

```yaml
name: fastapi
language: Python
description: Runnable FastAPI project generator
```

## Project Templates

Each target owns its project template foundation under the generator layer.

```text
generator/
├── php/
│   └── project_template/
├── fastapi/
│   └── project_template/
└── nestjs/
    └── project_template/
```

Project templates provide:

- README files
- `.env.example`
- Dockerfile
- `docker-compose.yml`
- framework bootstrap files
- project metadata
- test placeholders
- generator manifest

Target templates remain deterministic and local. They do not download dependencies or call remote services.

## Runnable Project Generation

### PHP

PHP output now includes a runnable project foundation:

```text
output/
├── public/
│   ├── index.php
│   └── .htaccess
├── app/
│   ├── Controllers/
│   ├── Services/
│   └── Models/
├── routes/
│   └── web.php
├── config/
│   ├── app.php
│   └── database.php
├── storage/
├── tests/
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── generator_manifest.json
```

Legacy PHP output files are still generated for compatibility.

### FastAPI

FastAPI output now includes an application package:

```text
output/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── middleware/
│   └── repositories/
├── tests/
├── requirements.txt
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── generator_manifest.json
```

Legacy FastAPI files remain at the previous output paths for compatibility.

### NestJS

NestJS output now includes project bootstrap files:

```text
output/
├── src/
├── test/
├── package.json
├── nest-cli.json
├── tsconfig.json
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── generator_manifest.json
```

## Generator Manifest

Every target writes:

```text
generator_manifest.json
```

Example:

```json
{
  "generator": "fastapi",
  "semarc_version": "0.12.0",
  "project": "Shop",
  "generated_at": "1970-01-01T00:00:00Z",
  "profiles": [],
  "modules": []
}
```

The timestamp is deterministic in v0.12.0 so golden tests remain stable.

## Validation

The release validation suite checks that generated projects contain:

- README
- `.env.example`
- Dockerfile
- `docker-compose.yml`
- generator manifest
- required target folders
- non-empty generated files
- no unresolved template placeholders
- no duplicate generated output paths

Where local tooling exists, generated syntax is checked:

- PHP files with `php -l`
- Python files with `py_compile`
- TypeScript files with structural checks

No validation requires internet access.

## Future Target Packages

The target foundation prepares SEMARC for future target packages.

Future target packages may provide:

- target metadata
- project templates
- framework bootstrap files
- target-specific validation rules
- optional generator adapters

v0.12.0 does not implement target downloads, target version resolution, marketplaces, or remote registries.

## Boundary

Project templates must stay in the generator layer.

They must not modify:

- lexer behavior
- parser behavior
- semantic AST
- Architecture IR semantics
- module resolution
- profile composition
- architecture intelligence

SEMARC Core remains the architecture engine. Targets build runnable project foundations from the stable Architecture IR.

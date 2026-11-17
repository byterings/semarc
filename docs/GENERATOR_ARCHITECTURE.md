# Generator Architecture

Generators map Architecture IR to runnable projects:

```text
Architecture IR -> Generation Contract -> Target Generator -> Runnable Project
```

Generators must not parse semantic source, decide architecture rules, infer routes or mutate
the AST. Every decision (operations, access, ownership, field rules, migration order) is
already in the IR.

## Shared Utilities

`generator/utils/` holds target-neutral helpers used by every generator:

| Module | Responsibility |
| --- | --- |
| `inflector.py` | pluralization and case conversion for resource names |
| `resource_views.py` | input/output field views, effective limits (255 for `STRING`, 72 for secrets), page sizes |
| `api_scenario.py` | builds `api_scenario.json`, the behavioural test plan |
| `project_runtime.py` | `.env.example`, `docker-compose.yml`, README shared by all targets |
| `template_engine.py` | `{{placeholder}}` rendering; fails on unresolved placeholders |

`generator/output_directory.py` prepares the output directory and
`generator/project_files.py` writes `generator_manifest.json`.

## PHP Generator

Entry point: `generator/php_generator.py`.

| Module | Output |
| --- | --- |
| `php/core_generator.py` | `core/` runtime (router, request/response, PDO, schema, migrator, repository and resource service bases), `validators/Validator.php`, auth classes |
| `php/model_generator.py` | `models/<Model>.php` field metadata and casting |
| `php/repository_generator.py` | `repositories/<Model>Repository.php` |
| `php/service_generator.py` | `services/<Model>Service.php` |
| `php/controller_generator.py` | `controllers/<Model>Controller.php` |
| `php/routes_generator.py` | `routes.php` with access flags |
| `php/migration_generator.py` | `migrations/NNN_create_<table>_table.php` |
| `php/project_generator.py` | bootstrap, `public/`, `config/`, `bin/migrate.php`, `tests/`, Docker, README |

Templates: `templates/php/core/`, `templates/php/auth/`, `templates/php/project/`.

## FastAPI Generator

Entry point: `generator/fastapi/fastapi_generator.py`.

| Module | Output |
| --- | --- |
| `fastapi/entity_code.py` | `models/`, `schemas/`, `repositories/`, `services/` per model |
| `fastapi/api_code.py` | `routers/<model>.py`, `routers/auth.py`, `routers/custom.py`, `main.py` |
| `fastapi/migration_code.py` | `migrations/versions/NNNN_create_<table>_table.py` (Alembic) |

Templates in `templates/fastapi/` cover settings-independent runtime files: error handlers,
database session, schema and repository/service bases, token service, password hasher,
auth dependency, Alembic configuration, `migrate.py`, the pytest runner and the Dockerfile.

## NestJS Generator

Entry point: `generator/nestjs/nestjs_generator.py`.

| Module | Output |
| --- | --- |
| `nestjs/entity_code.py` | entity, create/update DTOs, repository, service and module per model |
| `nestjs/api_code.py` | controllers, auth module, custom module, `app.module.ts`, `app.controller.ts`, data source, migrations, settings |
| `nestjs/typescript.py` | TypeScript naming and import helpers (aliases framework symbols that collide with model names) |

Templates in `templates/nestjs/` hold the shared runtime: error type and filter, validation
pipe, id pipe, resource repository and service bases, column type mapping, token service,
password hasher, guard, current-user decorator, `main.ts`, the Jest runner, tsconfig files
and the Dockerfile.

## Target Registration

Targets are described by `generator/<target>/project_template/target.yaml` and registered
by `TargetRegistry.builtins()`. `TargetGeneratorFactory` maps the registry entry to the
generator class.

## Contract Checks

After generation, `GeneratorArchitectureValidator` checks that every contract component has
its file, that routes reach controllers, controllers use services and services use
repositories, that the experience endpoints exist and that PHP `require_once` paths resolve.

## Debugging

`--debug` prints every created file and the template or generator that produced it.

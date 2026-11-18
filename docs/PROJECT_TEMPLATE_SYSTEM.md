# Project Template System

SEMARC Core is the architecture engine; targets are runnable project builders. Core owns
parsing, validation, profiles, modules, relationships, resource planning, diagnostics and
the Architecture IR. Targets own framework code, runtime files, Docker files, package
manifests and project layout.

## Shared Project Files

Every target writes:

| File | Purpose |
| --- | --- |
| `README.md` | quick start, Docker, tests, configuration, auth, API table, layout |
| `.env.example` | `APP_NAME`, `APP_ENV`, `DB_CONNECTION`, `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`, `CORS_ORIGINS`, and with auth `JWT_SECRET`, `JWT_TTL`, `AUTH_RATE_LIMIT`, `AUTH_RATE_WINDOW` |
| `Dockerfile` | production image; applies migrations on start |
| `docker-compose.yml` | the app plus MySQL 8.4 or PostgreSQL 17 (with health checks), or a SQLite volume; host port overridable with `APP_PORT` |
| `api_scenario.json` | behavioural test plan, replayed by the project's test runner |
| `.gitignore`, `storage/` | ignores `.env`, build output and SQLite files |
| `generator_manifest.json` | generator, SEMARC version, project, profiles, modules |
| `architecture_report.json` | diagnostics written by `DiagnosticReportPass` |

`DB_CONNECTION` accepts `mysql`, `pgsql` or `sqlite`. Relative SQLite paths resolve against
the project root. Environment variables take precedence over `.env`.

## PHP

```text
public/index.php        front controller (php -S ... public/index.php)
bootstrap.php           loads .env and every class
routes.php              routes, access flags, /, /health, /routes
core/                   Router, Request, Response, Database, Schema, Migrator,
                        Repository, ResourceService, Cast, Env, HttpException, HomePage, Jwt
models/ repositories/ services/ controllers/ validators/ middleware/
migrations/             NNN_create_<table>_table.php table definitions
bin/migrate.php         waits for the database, applies pending migrations
config/app.php, config/database.php
tests/run.php           replays tests/api_scenario.json in-process on SQLite
```

Run: `php bin/migrate.php && php -S 127.0.0.1:8000 -t public public/index.php`.
Tests: `php tests/run.php` (needs `pdo_sqlite`). PHP 8.1+ with `pdo_mysql`, `pdo_pgsql` or
`pdo_sqlite`; no Composer packages are required.

## FastAPI

```text
main.py                 app, error handlers, routers, /, /health, /routes
database.py             engine, session, Base
config/settings.py      environment settings and database URL
core/errors.py          ApiError and exception handlers
models/ schemas/ repositories/ services/ routers/ middleware/
migrations/             Alembic env and versions/NNNN_create_<table>_table.py
alembic.ini, migrate.py waits for the database, runs alembic upgrade head
tests/test_api.py       replays tests/api_scenario.json with TestClient on SQLite
requirements.txt        pinned dependencies
```

Run: `pip install -r requirements.txt && python migrate.py && uvicorn main:app`.
Tests: `pytest`. Interactive docs at `/docs`.

## NestJS

```text
src/main.ts, src/app.setup.ts, src/app.module.ts, src/app.controller.ts
src/config/settings.ts
src/common/             ApiError, exception filter, validation pipe, id pipe,
                        ResourceRepository, ResourceService, password hasher, CurrentUserId
src/database/           column types, data source, migrations/
src/modules/<resource>/ entity, dto/, repository, service, controller, module
src/modules/auth/       auth controller, module, token service, login DTO
src/guards/auth.guard.ts
test/api.e2e-spec.ts    replays test/api_scenario.json with supertest on in-memory SQLite
package.json, tsconfig.json, tsconfig.build.json, nest-cli.json
```

Run: `npm install && npm run start:dev` (migrations run on start). Tests: `npm test`.
Build: `npm run build && npm start`. Node.js 22+.

## Pinned Toolchains

| Target | Versions |
| --- | --- |
| PHP | PHP 8.3 image; no third-party packages |
| FastAPI | FastAPI 0.163, SQLAlchemy 2.1, Alembic 1.20, Pydantic 2.14, PyJWT 2.15, bcrypt 5, pytest 9 |
| NestJS | NestJS 11.2, TypeORM 0.3.31, @nestjs/jwt 11, class-validator 0.14, TypeScript 5.9, Jest 30 |

Versions are pinned exactly in `semarc/generator/fastapi/fastapi_generator.py` and
`semarc/generator/nestjs/nestjs_generator.py` so that generated projects are reproducible.

## Boundary

Project templates stay in the generator layer. They must not change lexer, parser, AST, IR
semantics, module resolution, profile composition or diagnostics.

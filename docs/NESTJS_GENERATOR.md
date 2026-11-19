# NestJS Generator

The NestJS generator was introduced in v0.10.0 as structural scaffolding and became a
runnable target in v0.14.0. It consumes the same Architecture IR as the PHP and FastAPI
generators and produces the same API behaviour (see `GENERATED_API.md`).

## Target Selection

```text
TARGET NESTJS
```

or `python3 main.py app.sem --target nestjs`.

## Stack

NestJS 11, TypeORM 0.3 (`mysql2`, `pg`, `better-sqlite3`), class-validator, @nestjs/jwt,
bcryptjs, TypeScript 5.9, Jest 30 with ts-jest and supertest. Versions are pinned in
`semarc/generator/nestjs/nestjs_generator.py`.

## Per-Model Output

For `MODEL Post` the generator writes `src/modules/posts/`:

| File | Content |
| --- | --- |
| `post.entity.ts` | TypeORM entity; column types follow `DB_CONNECTION` via `columnType()` |
| `dto/create-post.dto.ts` | class-validator rules for create and replace |
| `dto/update-post.dto.ts` | the same rules, every field optional, required fields not nullable |
| `posts.repository.ts` | `PostRepository extends ResourceRepository<Post>` |
| `posts.service.ts` | `PostService extends ResourceService<Post>` with output fields, references, dependents and unique columns |
| `posts.controller.ts` | one handler per declared route, full paths in the route decorators |
| `posts.module.ts` | wires TypeORM feature, repository, service and controller |

A model without routes (for example the auth-created `User`) gets no controller.

## Application Wiring

- `app.module.ts` configures TypeORM from `data-source.ts` with `migrationsRun: true` and
  connection retries, then imports the custom, auth and model modules.
- `app.setup.ts` installs the global exception filter and the strict validation pipe; the
  server and the tests share it.
- `app.controller.ts` serves `/`, `/health` (runs `SELECT 1`) and `/routes`.

## Authentication

`src/modules/auth/` provides `POST /register`, `POST /login` and `GET /me`. `TokenService`
signs HS256 tokens with `@nestjs/jwt`; `AuthGuard` verifies the bearer token, checks that
the user still exists and stores the id for `@CurrentUserId()`. The auth module is global so
feature modules can use the guard.

## Validation and Errors

The validation pipe uses `whitelist: true` (unknown fields are stripped) and no implicit
conversion (strict types). Failures become 422 with field details. Ids are parsed by
`IdPipe` (invalid ids are 404). The global filter renders every error in the shared
envelope, maps malformed JSON to 400 and database unique violations to 409.

## Migrations

`src/database/migrations/<timestamp>-create-<table>-table.ts` uses TypeORM's `Table` API, so
the same migration runs on MySQL, PostgreSQL and SQLite. Timestamps are deterministic
(`1700000000000 + sequence * 1000`). `npm run migration:run` applies them manually.

## Tests

`test/api.e2e-spec.ts` boots the application with an in-memory SQLite database
(`test/setup-env.ts`) and replays `test/api_scenario.json` step by step.

## Name Collisions

A model named like a framework symbol (`Post`, `Index`, `Column`, ...) is supported: generated
imports alias the framework symbol (`Post as PostDecorator`).

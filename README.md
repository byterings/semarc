# SEMARC

SEMARC is a Semantic Architecture Compiler.

It compiles a strict, declarative architecture specification into a runnable backend project:
database-backed CRUD APIs, JWT authentication, request validation, migrations, Docker
configuration and a test suite, for PHP, FastAPI or NestJS.

```text
Architecture Specification (.sem) -> Runnable Project
```

SEMARC is not a chatbot, an LLM application or a probabilistic code generator. Every
decision is made by explicit compiler passes and rules, and the same input always
produces the same output.

## Example

```text
PROJECT BlogAPI

TARGET FASTAPI

DATABASE POSTGRESQL

AUTH JWT

MODEL User
    name STRING
    email STRING UNIQUE
    password STRING

MODEL Post
    title STRING
    body TEXT
    views INTEGER OPTIONAL

RELATION User HAS_MANY Post

VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN 8
VALIDATE Post.title REQUIRED MAX 120

ROUTE GET /posts
ROUTE GET /posts/{id}
ROUTE POST /posts
ROUTE PATCH /posts/{id}
ROUTE DELETE /posts/{id}
ROUTE GET /users/{id}/posts PROTECTED
```

```bash
python3 main.py blog.sem --output blog-api
cd blog-api && docker compose up --build
```

The generated API stores data in PostgreSQL, exposes `POST /register`, `POST /login` and
`GET /me`, requires a bearer token for writes, validates input, sets `posts.user_id` from
the token, and refuses to delete a user who still owns posts.

## What gets generated

| | PHP | FastAPI | NestJS |
| --- | --- | --- | --- |
| Runtime | PHP 8.1+, no framework | FastAPI, Pydantic v2 | NestJS 11 |
| Persistence | PDO | SQLAlchemy 2 | TypeORM 0.3 |
| Migrations | `php bin/migrate.php` | Alembic (`python migrate.py`) | TypeORM, run on start |
| Auth | HS256 JWT, bcrypt | PyJWT, bcrypt | @nestjs/jwt, bcryptjs |
| Tests | `php tests/run.php` | `pytest` | `npm test` |
| Databases | MySQL, PostgreSQL, SQLite | MySQL, PostgreSQL, SQLite | MySQL, PostgreSQL, SQLite |

Every project also contains `.env.example`, a `Dockerfile`, a `docker-compose.yml` with the
selected database, a README, `generator_manifest.json` and `architecture_report.json`.

All targets share one API contract (see [docs/GENERATED_API.md](docs/GENERATED_API.md)):

- `GET /`, `GET /health` (with a database check) and `GET /routes`
- `{"data": ...}` responses; lists add `meta` with `total`, `limit`, `offset`
- an `error` object with `code`, `message` and field `details` for 400, 401, 404, 409, 422 and 501

## Semantic language

| Command | Example |
| --- | --- |
| `PROJECT` | `PROJECT BlogAPI` |
| `TARGET` | `TARGET PHP`, `TARGET FASTAPI`, `TARGET NESTJS` (default PHP) |
| `DATABASE` | `DATABASE MYSQL`, `DATABASE POSTGRESQL`, `DATABASE SQLITE` |
| `AUTH` | `AUTH JWT` |
| `MODEL` | `MODEL Post` followed by indented `name TYPE [UNIQUE] [OPTIONAL]` fields |
| `RELATION` | `RELATION User HAS_MANY Post` (`HAS_MANY`, `HAS_ONE`, `BELONGS_TO`) |
| `VALIDATE` | `VALIDATE password REQUIRED MIN 8`, `VALIDATE Post.title MAX 120` |
| `ROUTE` | `ROUTE GET /posts/{id}`, `ROUTE DELETE /posts/{id} PUBLIC` |
| `PROFILE` | `PROFILE ECOMMERCE` |
| `USE` | `USE payment.razorpay` |

Field types are `STRING`, `TEXT`, `INTEGER`, `FLOAT` and `BOOLEAN`. Routes are mapped to
operations by shape: `GET|POST /posts`, `GET|PUT|PATCH|DELETE /posts/{id}` and
`GET /users/{id}/posts`. Any other declared route is generated as an explicit `501` stub.
With `AUTH JWT`, reads are public and writes need a token unless a route says `PUBLIC` or
`PROTECTED`.

Free-form natural language is not supported. The full grammar is in
[docs/SEMANTIC_LANGUAGE_SPEC.md](docs/SEMANTIC_LANGUAGE_SPEC.md).

## Command line

```bash
python3 main.py examples/blog_api.sem                       # writes ./output
python3 main.py examples/blog_api.sem --target nestjs       # override TARGET
python3 main.py examples/blog_api.sem --output ../my-api    # choose the directory
python3 main.py examples/blog_api.sem --debug               # print tokens, AST, IR and passes
```

SEMARC only clears an output directory it generated earlier. Use `--force` to replace
any other non-empty directory. Generation stops before writing files if validation or
the architecture diagnostics report errors.

## Pipeline

```text
Semantic Source
-> Lexer -> Parser -> Semantic AST
-> Profile Composition -> Stdlib Module Resolution -> Semantic Validation
-> Module Constraints -> Relationship Pass -> Constraint Pass -> Architecture Analysis
-> Resource Planning + Architecture Rules + Dependency Graph -> Expansion
-> Architecture IR -> Optimization -> IR Contract
-> Generation Contract -> Target Generator -> Generated Artifact Validation
-> Runnable Project + architecture_report.json
```

Each stage lives in its own module: `lexer/`, `parser/`, `ast/`, `validator/`,
`architecture/` (rules, relationships, resource planning, constraints, analysis,
profiles, stdlib, optimizer, IR, contracts), `compiler/passes/` and `generator/`
(`php/`, `fastapi/`, `nestjs/`, shared `utils/`, `targets/`). Templates live under
`templates/<target>/`.

## Verification

```bash
python3 -m unittest discover -s tests     # offline unit, IR, golden and compliance tests
python3 scripts/validate_release.py        # every offline suite plus compile checks
python3 scripts/e2e_runtime.py             # Docker: every example x target x database, over HTTP
```

Each generated project contains `api_scenario.json`, a target-neutral list of HTTP steps
derived from the specification. The project's own test runner replays it in-process, and
`scripts/e2e_runtime.py` replays it against a live `docker compose` stack. Use
`--targets`, `--databases` and source paths to narrow a run, and `--keep` to inspect a stack.

After an intentional generator change, refresh the golden snapshots with
`python3 scripts/update_goldens.py` and review the diff.

## Documentation

- [docs/SEMANTIC_LANGUAGE_SPEC.md](docs/SEMANTIC_LANGUAGE_SPEC.md) language reference
- [docs/GENERATED_API.md](docs/GENERATED_API.md) behaviour of every generated API
- [docs/ARCHITECTURE_IR_SPEC.md](docs/ARCHITECTURE_IR_SPEC.md) the language-neutral IR
- [docs/COMPILER_PASSES.md](docs/COMPILER_PASSES.md) pass order and responsibilities
- [docs/GENERATOR_ARCHITECTURE.md](docs/GENERATOR_ARCHITECTURE.md) target generators
- [docs/PROJECT_TEMPLATE_SYSTEM.md](docs/PROJECT_TEMPLATE_SYSTEM.md) generated project layouts
- [docs/ROADMAP.md](docs/ROADMAP.md) status and plans
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) how to extend SEMARC

Generated projects belong to you after generation; see
[docs/SEMARC_OWNERSHIP_MODEL.md](docs/SEMARC_OWNERSHIP_MODEL.md).

# SEMARC

SEMARC is a prototype Semantic Architecture Compiler.

It converts strict semantic architecture intent into deterministic runnable project foundations:

```text
Semantic Source
-> Lexer
-> Parser
-> Semantic AST
-> Semantic Validator
-> Relationship Pass
-> Constraint Analysis
-> Architecture Analysis
-> Architecture Rule Engine
-> Dependency Graph Builder
-> Architecture Expansion
-> Architecture IR
-> Optimization Pass
-> Target Profile Selection
-> Runnable Project Builder
```

SEMARC is not a chatbot system, not an LLM application, and not token prediction. It is a compiler-oriented prototype with strict input rules and deterministic output.

Current product direction:

```text
Architecture Specification -> Runnable Project Generator
```

SEMARC Core is the architecture engine. Targets are runnable project builders.

## Semantic Language

Supported V1 commands:

- `PROJECT`
- `DATABASE`
- `AUTH`
- `MODEL`
- `ROUTE`
- `TARGET`
- `RELATION`
- `VALIDATE`
- `PROFILE`
- `USE`

Example:

```text
PROJECT BlogAPI

TARGET FASTAPI

DATABASE MYSQL

AUTH JWT

MODEL User
    name STRING
    email STRING
    password STRING

ROUTE POST /login
ROUTE GET /users
```

Relationship example:

```text
RELATION User HAS_MANY Post
RELATION Post BELONGS_TO User
```

The language is intentionally strict. Free-form natural language is not supported.

`PROFILE` and `USE` are foundation hooks for future profile/package metadata.
They are optional and do not change current generated output.

## Run

```bash
python3 main.py examples/blog_api.sem
```

Debug the compiler pipeline:

```bash
python3 main.py examples/blog_api.sem --debug
```

Override the semantic target from the CLI:

```bash
python3 main.py examples/blog_api.sem --target fastapi --debug
```

Generate NestJS output:

```bash
python3 main.py examples/blog_api.sem --target nestjs
```

`--debug` prints:

- tokens
- semantic AST
- target profile
- dependency graph
- relationship graph
- migration plan
- compiler passes
- constraint diagnostics
- architecture expansion
- architecture IR
- generated component/template mapping

## Output

Generated PHP projects are written to `output/`:

```text
output/
├── public/
├── config/
├── tests/
├── controllers/
├── models/
├── repositories/
├── services/
├── validators/
├── migrations/
├── routes.php
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── generator_manifest.json
```

For the example input, SEMARC generates:

- `output/public/index.php`
- `output/routes.php`
- `output/controllers/AuthController.php`
- `output/controllers/UserController.php`
- `output/models/User.php`
- `output/services/UserService.php`
- `output/repositories/UserRepository.php`
- `output/README.md`
- `output/.env.example`
- `output/Dockerfile`
- `output/docker-compose.yml`
- `output/generator_manifest.json`

Additional generated files include:

- `output/migrations/create_users_table.sql`
- `output/migrations/CreateUsersTable.php`
- `output/services/TokenService.php`
- `output/services/PasswordHasher.php`
- `output/validators/Validator.php`
- `output/config/database.php`

For `TARGET FASTAPI`, SEMARC generates:

- `output/main.py`
- `output/routers/`
- `output/models/`
- `output/schemas/`
- `output/services/`
- `output/repositories/`
- `output/middleware/`
- `output/tests/`
- `output/requirements.txt`
- `output/README.md`
- `output/.env.example`
- `output/Dockerfile`
- `output/docker-compose.yml`
- `output/generator_manifest.json`

Legacy compatibility files are also still generated, including:

- `output/main.py`
- `output/config/settings.py`
- `output/routers/auth.py`
- `output/models/`
- `output/schemas/`
- `output/services/`
- `output/middleware/`
- `output/repositories/`
- `output/migrations/`

For `TARGET NESTJS`, SEMARC generates:

- `output/src/app.module.ts`
- `output/src/modules/`
- `output/src/modules/<resource>/<resource>.module.ts`
- `output/src/modules/<resource>/<resource>.service.ts`
- `output/src/modules/<resource>/<resource>.controller.ts`
- `output/src/modules/<resource>/<model>.model.ts`
- `output/src/guards/auth.guard.ts` when auth scaffolding is needed
- `output/test/`
- `output/package.json`
- `output/nest-cli.json`
- `output/tsconfig.json`
- `output/README.md`
- `output/.env.example`
- `output/Dockerfile`
- `output/docker-compose.yml`
- `output/generator_manifest.json`

## Architecture

- `lexer/lexer.py` tokenizes strict semantic source lines.
- `parser/parser.py` parses deterministic grammar.
- `ast/nodes.py` defines language-independent semantic nodes.
- `ast/ast_builder.py` centralizes AST construction.
- `validator/validator.py` validates semantic rules.
- `architecture/rules_engine.py` applies deterministic architecture rules.
- `architecture/dependency_graph.py` models component dependencies.
- `architecture/relationship_engine.py` builds relationship graphs, foreign keys, and migration plans.
- `architecture/strategy_engine.py` selects target implementation profiles.
- `architecture/constraints/` runs deterministic semantic architecture diagnostics.
- `architecture/analysis/` runs deterministic architecture reasonableness analysis.
- `architecture/profiles/` loads future profile metadata.
- `architecture/packages/` loads future package metadata.
- `architecture/stdlib/` discovers metadata-only stdlib modules.
- `architecture/expander.py` expands semantic intent into architecture components.
- `architecture/ir_builder.py` builds language-neutral implementation IR.
- `generator/php/` maps IR to PHP files.
- `generator/fastapi/` maps the same IR to FastAPI files.
- `generator/nestjs/` maps the same IR to NestJS TypeScript files.
- `generator/targets/` stores target metadata foundations for future target packages.
- `generator/fastapi/mappers/` maps language-neutral IR components to FastAPI-specific files.
- `templates/php/` contains simple placeholder templates.
- `templates/fastapi/` contains FastAPI templates.
- `templates/nestjs/` contains NestJS templates.
- `compiler/passes/` contains isolated compiler passes.
- `compiler/diagnostics/` defines diagnostic errors, warnings, and recommendations.
- `main.py` runs the full compiler pipeline.

## AST Philosophy

The AST represents semantic architecture meaning only:

- project identity
- database intent
- auth intent
- models
- fields
- routes
- target profile
- relations
- validations
- foreign keys
- migration metadata

The AST does not contain PHP syntax, framework code, folder paths, or generated source strings.

## Target Profiles

`TARGET` selects a backend profile:

```text
TARGET PHP
TARGET FASTAPI
TARGET NESTJS
```

If no target is provided, SEMARC defaults to `PHP` to preserve the original prototype behavior.

## Architecture Expansion

Architecture expansion turns compact semantic intent into implementation-neutral architecture pieces.

Example:

```text
AUTH JWT
```

expands into:

- auth controller
- token service
- password hashing service
- auth middleware
- user repository
- input validator
- token validation capability

This happens before code generation.

## Generation Pipeline

Generators consume Architecture IR, not raw parser output.

Since v0.12.0, generators are runnable project builders. They generate framework code, README files, environment examples, Docker defaults, project bootstrap files, and `generator_manifest.json`.

The Generation Contract Foundation validates that model-backed routes, business services, persistence components, and entities are wired as one coherent architecture before and after target generation.

Since v0.13.0, generated projects expose:

- `/`
- `/health`
- `/routes`

Every model receives a reachable resource route using shared pluralization.

The PHP generator is split by concern:

- `routes_generator.py`
- `model_generator.py`
- `auth_generator.py`
- `repository_generator.py`
- `validator_generator.py`
- `template_engine.py`

This keeps parser logic, architecture logic, and PHP code generation separate.

Generated auth components are explicit TODO scaffolds. SEMARC does not generate fake JWT, demo tokens, or pretend authentication runtime behavior.

The NestJS generator emits structural TypeScript scaffolding for modules, models, services, controllers, app module registration, and placeholder auth guards. It does not implement real authentication, persistence, or runtime NestJS integrations yet.

See `docs/PROJECT_TEMPLATE_SYSTEM.md` for the project template system.
See `docs/GENERATION_CONTRACT.md` for generation contract and target compliance rules.
See `docs/TARGET_REGISTRY.md` for target registry and manifest rules.

## Architecture Diagnostics

SEMARC runs a deterministic constraint engine before architecture expansion and writes a final report after generation:

```text
output/architecture_report.json
```

The report includes:

- errors
- warnings
- recommendations
- architecture score
- executed rule count
- architecture analysis warnings and recommendations
- project summary
- generator target
- compiler statistics
- dependency and constraint summaries

## Release Validation

Run the full release validation workflow with:

```bash
python3 scripts/validate_release.py
```

The script runs unit, integration, golden, regression, release, stress, generator validation, and compile checks.

Diagnostics are produced only by explicit rules. They are not AI-generated.

## Stdlib Modules

`USE` declarations now validate against discovered stdlib modules.

Modules live under `stdlib/**/module.yaml` and are metadata-only in v0.5.0:

```text
USE auth.jwt
USE cache.redis
```

Unknown `USE` entries remain valid metadata for v0.4 compatibility. Known
stdlib modules are resolved into the architecture report.

Resolved modules may also declare:

- `depends`
- `requires`
- `conflicts`

Module constraints are validated after dependency resolution. For example,
`payment.razorpay` can require `database.mysql`, and `auth.jwt` can conflict
with `auth.session`.

## Tests

Run the focused compiler tests:

```bash
python3 -m unittest discover -s tests
```

The tests cover relationship parsing, migration planning, compiler pass execution, constraint diagnostics, and deterministic generation.

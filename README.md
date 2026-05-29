# SEMARC

SEMARC is a prototype Semantic Architecture Compiler.

It converts strict semantic architecture intent into deterministic backend code:

```text
Semantic Source
-> Lexer
-> Parser
-> Semantic AST
-> Semantic Validator
-> Relationship Pass
-> Constraint Analysis
-> Architecture Rule Engine
-> Dependency Graph Builder
-> Architecture Expansion
-> Architecture IR
-> Optimization Pass
-> Target Profile Selection
-> PHP Generator
```

SEMARC is not a chatbot system, not an LLM application, and not token prediction. It is a compiler-oriented prototype with strict input rules and deterministic output.

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

Generated PHP files are written to `output/`:

```text
output/
├── routes.php
├── controllers/
├── models/
├── middleware/
├── repositories/
├── migrations/
├── services/
├── validators/
└── config/
```

For the example input, SEMARC generates:

- `output/routes.php`
- `output/controllers/AuthController.php`
- `output/models/User.php`
- `output/middleware/AuthMiddleware.php`
- `output/repositories/UserRepository.php`
- `output/migrations/create_users_table.sql`
- `output/migrations/CreateUsersTable.php`
- `output/services/TokenService.php`
- `output/services/PasswordHasher.php`
- `output/validators/Validator.php`
- `output/config/database.php`

For `TARGET FASTAPI`, SEMARC generates:

- `output/main.py`
- `output/config/settings.py`
- `output/routers/auth.py`
- `output/models/`
- `output/schemas/`
- `output/services/`
- `output/middleware/`
- `output/repositories/`
- `output/migrations/`

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
- `architecture/profiles/` loads future profile metadata.
- `architecture/packages/` loads future package metadata.
- `architecture/expander.py` expands semantic intent into architecture components.
- `architecture/ir_builder.py` builds language-neutral implementation IR.
- `generator/php/` maps IR to PHP files.
- `generator/fastapi/` maps the same IR to FastAPI files.
- `generator/fastapi/mappers/` maps language-neutral IR components to FastAPI-specific files.
- `templates/php/` contains simple placeholder templates.
- `templates/fastapi/` contains FastAPI templates.
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

The PHP generator is split by concern:

- `routes_generator.py`
- `model_generator.py`
- `auth_generator.py`
- `repository_generator.py`
- `validator_generator.py`
- `template_engine.py`

This keeps parser logic, architecture logic, and PHP code generation separate.

Generated services and middleware contain prototype implementation logic, including password hashing, token generation, token validation, authorization-header handling, basic repository methods, and request validation helpers.

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

Diagnostics are produced only by explicit rules. They are not AI-generated.

## Tests

Run the focused compiler tests:

```bash
python3 -m unittest discover -s tests
```

The tests cover relationship parsing, migration planning, compiler pass execution, constraint diagnostics, and deterministic generation.

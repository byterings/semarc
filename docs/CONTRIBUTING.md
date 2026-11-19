# Contributing

This document explains how to extend SEMARC without breaking compiler boundaries.

## Project Identity

SEMARC is not an AI agent framework or chatbot project.

SEMARC is a deterministic semantic compiler and architecture synthesis engine.

## Coding Standards

- keep code beginner-readable
- prefer small modules
- use explicit names
- avoid hidden magic
- keep target-specific code inside generators
- keep semantic logic inside compiler or architecture layers

## Compiler Boundary Rules

### Lexer

May:

- split source into tokens
- classify basic token types

Must not:

- validate model existence
- generate AST
- infer architecture

### Parser

May:

- parse grammar
- create AST nodes through AST builder

Must not:

- generate code
- select target strategy
- infer dependency graph

### Validator

May:

- reject invalid semantic programs
- produce readable semantic errors

Must not:

- generate architecture components
- write files

### Architecture Layer

May:

- apply rules
- build dependency graph
- build relationship graph
- create migration plan
- build IR

Must not:

- render templates
- write target files

### Generators

May:

- map IR to target code
- render templates
- write files

Must not:

- parse semantic source
- decide semantic architecture rules
- mutate AST

## Adding a Semantic Command

Prefer stdlib modules or profiles over new keywords. When a keyword is necessary:

1. Add the lexer keyword (`SERVICE` and `CONFIG` are already reserved).
2. Add or extend AST nodes and the AST builder.
3. Add the parser rule.
4. Add validation in `semarc/validator/validator.py`.
5. Plan its meaning in `architecture/` (usually `resource_planner.py`).
6. Add IR metadata and document it in `docs/ARCHITECTURE_IR_SPEC.md`.
7. Map it in every target and extend `semarc/generator/utils/api_scenario.py` so the behaviour is tested.
8. Add language, IR and compliance tests; update docs.

## Adding a Target

1. Add the profile in `strategy_engine.py` and the name in `SemanticValidator.SUPPORTED_TARGETS`.
2. Add `semarc/generator/<target>/project_template/target.yaml` and the generator.
3. Register it in `TargetGeneratorFactory`.
4. Add templates under `semarc/templates/<target>/`.
5. Translate the IR using `semarc/generator/utils/` (resource views, scenario, runtime files).
6. Ship a runner for `api_scenario.json`, add compliance tests, pass `scripts/e2e_runtime.py`.

## Naming Conventions

- AST nodes end with `Node`.
- Compiler passes end with `Pass`.
- Generators end with `Generator`.
- FastAPI mappers end with `Mapper`.
- Templates use `.tpl`.

## Development Setup

```bash
git clone https://github.com/byterings/semarc && cd semarc
python3 -m venv .venv && . .venv/bin/activate
pip install -e .                      # the semarc command, running from this checkout
pip install openapi-spec-validator    # optional: enables the OpenAPI validity test
```

All compiler code lives in the `semarc/` package; data files (templates, stdlib modules,
profiles, starters, target manifests) are package data inside it.

## Testing

```bash
python3 -m unittest discover -s tests      # all offline tests
python3 scripts/validate_release.py         # every suite plus compile checks
python3 scripts/update_goldens.py           # after an intentional generator change; review the diff
python3 scripts/project_tests.py examples/blog_api.sem   # Docker: each generated project's own test suite
python3 scripts/e2e_runtime.py              # Docker: examples x targets x databases over HTTP
```

Narrow an end-to-end run with source paths, `--targets` and `--databases`, for example
`python3 scripts/e2e_runtime.py examples/blog_api.sem --targets php --databases sqlite`.

## Continuous Integration

`.github/workflows/ci.yml` runs on pushes to `master` and `dev` and on pull requests:

- **Release validation**: `scripts/validate_release.py` on Python 3.12, with PHP for syntax
  checks and `openapi-spec-validator` for the OpenAPI test.
- **Runtime**: one job per target runs `scripts/e2e_runtime.py` for `examples/blog_api.sem`
  and `tests/fixtures/edge_public.sem` on SQLite and PostgreSQL in Docker.

The full matrix (every example, target and database) is slower; run it locally before a release.

## Documentation

Update `docs/` when changing architecture behavior.

Update `README.md` when changing user-facing commands or outputs.

Update `AGENTS.md` when changing contributor rules or boundaries.

## Releasing

See [RELEASING.md](RELEASING.md).

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
4. Add validation in `validator/validator.py`.
5. Plan its meaning in `architecture/` (usually `resource_planner.py`).
6. Add IR metadata and document it in `docs/ARCHITECTURE_IR_SPEC.md`.
7. Map it in every target and extend `generator/utils/api_scenario.py` so the behaviour is tested.
8. Add language, IR and compliance tests; update docs.

## Adding a Target

1. Add the profile in `strategy_engine.py` and the name in `SemanticValidator.SUPPORTED_TARGETS`.
2. Add `generator/<target>/project_template/target.yaml` and the generator.
3. Register it in `TargetGeneratorFactory`.
4. Add templates under `templates/<target>/`.
5. Translate the IR using `generator/utils/` (resource views, scenario, runtime files).
6. Ship a runner for `api_scenario.json`, add compliance tests, pass `scripts/e2e_runtime.py`.

## Naming Conventions

- AST nodes end with `Node`.
- Compiler passes end with `Pass`.
- Generators end with `Generator`.
- FastAPI mappers end with `Mapper`.
- Templates use `.tpl`.

## Testing

```bash
python3 -m unittest discover -s tests      # all offline tests
python3 scripts/validate_release.py         # every suite plus compile checks
python3 scripts/update_goldens.py           # after an intentional generator change; review the diff
python3 scripts/e2e_runtime.py              # Docker: examples x targets x databases over HTTP
```

Narrow an end-to-end run with source paths, `--targets` and `--databases`, for example
`python3 scripts/e2e_runtime.py examples/blog_api.sem --targets php --databases sqlite`.

## Documentation

Update `docs/` when changing architecture behavior.

Update `README.md` when changing user-facing commands or outputs.

Update `AGENTS.md` when changing contributor rules or boundaries.

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

1. Add lexer keyword.
2. Add AST node if needed.
3. Add parser rule.
4. Add validation.
5. Add architecture expansion.
6. Add IR metadata.
7. Add target mappings.
8. Add tests.
9. Update docs.

## Adding a Target

1. Add profile in `strategy_engine.py`.
2. Add generator under `generator/<target>/`.
3. Add templates under `templates/<target>/`.
4. Map existing IR components.
5. Add compile/lint tests where possible.

## Naming Conventions

- AST nodes end with `Node`.
- Compiler passes end with `Pass`.
- Generators end with `Generator`.
- FastAPI mappers end with `Mapper`.
- Templates use `.tpl`.

## Testing

Run:

```bash
python3 -m unittest discover -s tests
python3 -m compileall main.py architecture compiler generator lexer parser validator tests ast_loader.py
```

If PHP output changes, run:

```bash
php -l output/routes.php
php -l output/models/User.php
```

If FastAPI output changes, run:

```bash
python3 -m py_compile output/main.py
```

## Documentation

Update `docs/` when changing architecture behavior.

Update `README.md` when changing user-facing commands or outputs.

Update `AGENTS.md` when changing contributor rules or boundaries.

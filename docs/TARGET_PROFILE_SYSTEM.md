# Target Profile System

Target profiles let SEMARC generate different backend frameworks from the same semantic architecture.

## Purpose

The target profile separates semantic architecture from implementation strategy.

Semantic intent:

```text
AUTH JWT
MODEL User
ROUTE POST /login
```

Target strategies:

```text
PHP
FASTAPI
```

## Target Selection

Semantic source may declare:

```text
TARGET PHP
TARGET FASTAPI
```

CLI may override:

```bash
python3 main.py examples/blog_api.sem --target fastapi
```

If no target is selected, SEMARC defaults to PHP.

## Profile Shape

Example:

```json
{
  "target": "FASTAPI",
  "generator": "fastapi",
  "framework": "fastapi",
  "auth_strategy": "lightweight_custom_token",
  "repository_strategy": "in_memory_prototype"
}
```

## Current Profiles

```text
PHP
FASTAPI
LARAVEL
NODE
```

Only PHP and FastAPI have implemented generators. Laravel and Node are placeholder strategy profiles.

## Strategy Engine

`architecture/strategy_engine.py` selects target profile.

The strategy engine does not generate code. It selects implementation strategy metadata used later by generation.

## Same IR, Different Output

```text
Architecture IR
    |
    +-- PHP Generator
    |
    +-- FastAPI Generator
```

The IR remains shared and language-independent.

## Extension Rules

To add a target:

1. Add target profile.
2. Add generator entry point.
3. Add target templates.
4. Map existing IR components.
5. Keep architecture rules unchanged unless semantics require new components.

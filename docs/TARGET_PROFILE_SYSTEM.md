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

```text
TARGET PHP
TARGET FASTAPI
TARGET NESTJS
```

The CLI can override the source: `python3 main.py app.sem --target fastapi`. Without a
target SEMARC uses PHP. Any other name (including `LARAVEL` and `NODE`) is rejected with
the list of available targets, both in source and on the command line.

## Profile Shape

```json
{
  "target": "FASTAPI",
  "generator": "fastapi",
  "framework": "fastapi",
  "auth_strategy": "jwt_hs256",
  "repository_strategy": "sqlalchemy"
}
```

## Current Profiles

| Target | Generator | Auth | Persistence |
| --- | --- | --- | --- |
| `PHP` | php | `jwt_hs256` | `pdo` |
| `FASTAPI` | fastapi | `jwt_hs256` | `sqlalchemy` |
| `NESTJS` | nestjs | `jwt_hs256` | `typeorm` |

## Strategy Engine

`architecture/strategy_engine.py` selects the target profile. It records implementation
strategy metadata; it does not generate code and never falls back to another target.

## Same IR, Different Output

```text
Architecture IR
    |
    +-- PHP Generator
    +-- FastAPI Generator
    +-- NestJS Generator
```

## Extension Rules

To add a target:

1. Add the profile to `StrategyEngine.TARGET_PROFILES` and the name to
   `SemanticValidator.SUPPORTED_TARGETS`.
2. Add `generator/<target>/project_template/target.yaml` and the generator class.
3. Register it in `TargetGeneratorFactory`.
4. Map the IR without adding architecture rules; reuse `generator/utils/`.
5. Ship a runner for `api_scenario.json` and pass `scripts/e2e_runtime.py`.

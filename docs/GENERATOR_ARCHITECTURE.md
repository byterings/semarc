# Generator Architecture

Generators map Architecture IR to target-specific runnable project foundations.

Generators must only perform target mapping:

```text
Architecture IR -> Runnable Project
```

Generators must not parse semantic source or invent architecture decisions.

## Generator Boundary

Allowed in generators:

- choosing target file names
- rendering templates
- mapping IR fields to target syntax
- writing generated files
- writing target project bootstrap files
- writing README, environment, Docker, and manifest files

Not allowed in generators:

- semantic validation
- relationship inference
- dependency graph construction
- AST mutation
- architecture rule selection

## Current Generators

```text
generator/
    php/
    fastapi/
    nestjs/
    targets/
```

## PHP Generator

Entry point:

```text
generator/php_generator.py
```

Modules:

```text
generator/php/routes_generator.py
generator/php/model_generator.py
generator/php/auth_generator.py
generator/php/repository_generator.py
generator/php/validator_generator.py
generator/php/migration_generator.py
generator/php/template_engine.py
```

Output:

```text
output/
├── public/
├── app/
├── routes/
├── storage/
├── tests/
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── generator_manifest.json
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

## FastAPI Generator

Entry point:

```text
generator/fastapi/fastapi_generator.py
```

Mappers:

```text
generator/fastapi/mappers/
├── config_mapper.py
├── controller_mapper.py
├── middleware_mapper.py
├── migration_mapper.py
├── model_mapper.py
├── repository_mapper.py
├── service_mapper.py
└── name_utils.py
```

Output:

```text
output/
├── app/
├── tests/
├── requirements.txt
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── generator_manifest.json
├── main.py
├── config/
├── routers/
├── services/
├── middleware/
├── models/
├── schemas/
├── repositories/
└── migrations/
```

## NestJS Generator

Entry point:

```text
generator/nestjs/nestjs_generator.py
```

Output:

```text
output/
├── src/
├── test/
├── package.json
├── nest-cli.json
├── tsconfig.json
├── README.md
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── generator_manifest.json
```

## Target Foundation

Target metadata foundations live under:

```text
generator/targets/
generator/php/project_template/
generator/fastapi/project_template/
generator/nestjs/project_template/
```

Built-in targets are registered through `TargetRegistry`.

## Template System

Templates live under:

```text
templates/php/
templates/fastapi/
templates/nestjs/
```

The template engine supports deterministic placeholder replacement:

```text
{{class_name}}
{{model_name}}
{{fields}}
```

This is intentionally simple. SEMARC does not need a full templating language yet.

## Target Mappers

FastAPI uses mappers to keep framework adaptation explicit.

Example:

```text
IR controller: AuthController
FastAPI mapper: routers/auth.py
```

This avoids forcing PHP-style controller structure onto FastAPI.

## Debugging

Debug mode prints generated component mappings:

```text
[Generator]
Created: models/User.php
Template: model.tpl
```

FastAPI debug also prints mapper selections:

```text
[FastAPI Mappers]
Mapper: ModelMapper
Output: models/user.py
Template: model.tpl
```

# NestJS Generator

The NestJS generator was introduced in SEMARC v0.10.0.

It demonstrates that the same semantic architecture can be compiled into a third backend target without changing the semantic language, AST, module system, profile system, Architecture IR, or architecture intelligence layer.

The generator consumes Architecture IR and maps it to a minimal NestJS TypeScript project structure.

## Target Selection

Use:

```text
TARGET NESTJS
```

or override the target from the CLI:

```bash
python3 main.py examples/blog_api.sem --target nestjs
```

Target names are case-insensitive through the existing target selection path.

## Example Semantic Source

```text
PROJECT Shop

TARGET NESTJS

DATABASE MYSQL

AUTH JWT

MODEL User
    email STRING
    name STRING

ROUTE GET /users
ROUTE POST /users
ROUTE POST /login
```

No new grammar is required for NestJS generation.

Services are generated from semantic models in the current compiler. v0.10.0 does not add a new `SERVICE` parser branch.

## Generated Structure

Generated files are written to `output/src/`.

Example:

```text
output/
└── src/
    ├── app.module.ts
    ├── guards/
    │   └── auth.guard.ts
    └── modules/
        ├── auth/
        │   ├── auth.controller.ts
        │   ├── auth.module.ts
        │   └── auth.service.ts
        └── users/
            ├── user.model.ts
            ├── users.controller.ts
            ├── users.module.ts
            └── users.service.ts
```

The folder layout follows common NestJS conventions:

- `src/app.module.ts` registers generated modules.
- `src/modules/<resource>/` contains resource modules.
- `src/guards/` contains placeholder auth guard scaffolding.

## Model Generation

Each semantic `MODEL` becomes a TypeScript model class.

Example:

```text
MODEL User
    email STRING
    active BOOLEAN
```

Generated:

```typescript
export class User {
    email!: string;
    active!: boolean;
}
```

Type mapping is intentionally small:

```text
STRING  -> string
TEXT    -> string
INTEGER -> number
FLOAT   -> number
BOOLEAN -> boolean
```

## Service Generation

Each model receives a minimal NestJS service skeleton.

Example:

```typescript
import { Injectable } from '@nestjs/common';
import { User } from './user.model';

@Injectable()
export class UserService {
    findAll(): User[] {
        return [];
    }

    create(payload: Partial<User>): User {
        return payload as User;
    }
}
```

The service is structural only. It does not implement persistence, business logic, caching, or validation behavior.

## Controller Generation

Routes are mapped to resource controllers when the first route segment matches a model name.

Example:

```text
MODEL User
    email STRING

ROUTE GET /users
ROUTE POST /users
```

Generated:

```typescript
import { Controller, Get, Post } from '@nestjs/common';
import { UserService } from './users.service';

@Controller('users')
export class UserController {
    constructor(private readonly userService: UserService) {}

    @Get()
    findAll() {
        return this.userService.findAll();
    }

    @Post()
    createUser() {
        return this.userService.findAll();
    }
}
```

Current route mapping is deliberately simple:

- `GET /users` maps to `@Get()`.
- `POST /users` maps to `@Post()`.
- nested route suffixes are passed into the decorator path.

## Authentication Scaffold

When semantic auth exists, or a `/login` route exists, the NestJS generator creates placeholder auth files:

```text
src/
├── guards/
│   └── auth.guard.ts
└── modules/
    └── auth/
        ├── auth.controller.ts
        ├── auth.module.ts
        └── auth.service.ts
```

The generated guard is intentionally permissive:

```typescript
import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';

@Injectable()
export class AuthGuard implements CanActivate {
    canActivate(context: ExecutionContext): boolean {
        return true;
    }
}
```

This is scaffold only. Real authentication is outside v0.10.0 scope.

## App Module

`app.module.ts` imports and registers generated modules.

Example:

```typescript
import { Module } from '@nestjs/common';
import { UserModule } from './modules/users/users.module';
import { AuthModule } from './modules/auth/auth.module';

@Module({
    imports: [
        UserModule,
        AuthModule,
    ],
})
export class AppModule {}
```

Module registration order is deterministic and follows the Architecture IR model order, with auth scaffolding appended when present.

## Generator Boundary

The NestJS generator only maps:

```text
Architecture IR -> NestJS TypeScript files
```

It does not:

- parse semantic source
- modify semantic AST
- modify profiles
- modify stdlib modules
- run architecture intelligence
- change dependency resolution
- change module constraints

## Current Limitations

The v0.10.0 NestJS generator is structural.

It does not implement:

- real authentication
- database integration
- ORM entities
- dependency injection customization
- Swagger
- GraphQL
- WebSockets
- microservices
- NestJS plugins
- advanced decorators
- runtime behavior

These are intentionally excluded so v0.10.0 can focus on target portability.

## Verification

The generator is covered by tests for:

- target selection
- project structure
- model files
- service files
- controller files
- auth scaffold files
- app module registration
- multi-model projects
- profile-based projects
- dependency-based projects
- PHP and FastAPI backward compatibility

The test suite does not require `npm install`.

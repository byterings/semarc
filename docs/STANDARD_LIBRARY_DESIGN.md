# Standard Library Design

SEMARC can eventually support a semantic standard library of reusable architecture modules.

The standard library is not implemented yet. This document defines the design direction.

## Goal

Provide reusable semantic architecture modules such as:

```text
AUTH JWT
VALIDATE email REQUIRED EMAIL
RELATION User HAS_MANY Post
DATABASE MYSQL
```

These should compile into architecture components consistently across targets.

## Proposed Structure

```text
stdlib/
├── auth/
│   ├── jwt.semdef
│   └── session.semdef
├── validation/
│   ├── required.semdef
│   ├── email.semdef
│   └── min.semdef
├── relationships/
│   ├── has_many.semdef
│   ├── belongs_to.semdef
│   └── has_one.semdef
└── database/
    ├── mysql.semdef
    └── postgres.semdef
```

## Stdlib Responsibilities

The standard library should define:

- semantic capabilities
- required architecture components
- validation rules
- target mapping hints
- compatibility constraints

## Boundary

Stdlib modules should not contain final generated code.

They may define reusable architecture facts such as:

```text
AUTH JWT requires TokenService
AUTH JWT requires AuthMiddleware
AUTH JWT requires PasswordHasher
```

Target generators still decide how to render those components.

## Example Future Module

```text
module auth.jwt

requires service TokenService
requires service PasswordHasher
requires middleware AuthMiddleware
requires validator Validator
```

## Design Principles

- deterministic
- target-neutral
- composable
- versioned
- testable

## Future Use

Eventually, users may write:

```text
USE auth.jwt
USE database.mysql
```

For now, SEMARC keeps syntax explicit and simple.

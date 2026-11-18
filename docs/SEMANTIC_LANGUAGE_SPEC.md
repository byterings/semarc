# Semantic Language Specification

The SEMARC semantic language is a strict declarative architecture language. It describes
what backend architecture should exist, not how code should execute.

## Design Properties

The language is declarative, deterministic and line based. Indentation is used only for
model fields. It is not procedural code, natural language, prompt syntax or framework syntax.

## Lexical Rules

- Source is processed line by line; blank lines are ignored.
- Command keywords are uppercase and case sensitive (`MODEL Profile` declares a model named
  `Profile`; `PROFILE` is the command).
- Field types, relation types, field modifiers, route access and validation rules are uppercase.
- Paths start with `/`. Integers are written as digits.

## Commands

```text
PROJECT   TARGET   PROFILE   USE   DATABASE   AUTH
MODEL     RELATION ROUTE     VALIDATE
```

`SERVICE` and `CONFIG` are reserved for future versions and are rejected with an explicit error.

## Grammar

```text
program       := statement*
statement     := project | target | profile | use | database | auth
               | model | relation | route | validate

project       := "PROJECT" IDENTIFIER
target        := "TARGET" ("PHP" | "FASTAPI" | "NESTJS")
profile       := "PROFILE" IDENTIFIER
use           := "USE" MODULE_NAME
database      := "DATABASE" ("MYSQL" | "POSTGRESQL" | "SQLITE")
auth          := "AUTH" "JWT"
model         := "MODEL" MODEL_NAME NEWLINE field*
field         := INDENT FIELD_NAME TYPE modifier*
modifier      := "UNIQUE" | "OPTIONAL"
relation      := "RELATION" MODEL_NAME RELATION_TYPE MODEL_NAME
route         := "ROUTE" HTTP_METHOD PATH access?
access        := "PUBLIC" | "PROTECTED"
validate      := "VALIDATE" (FIELD_NAME | MODEL_NAME "." FIELD_NAME) rule+
rule          := "REQUIRED" | "EMAIL" | "MIN" INTEGER? | "MAX" INTEGER

TYPE          := "STRING" | "TEXT" | "INTEGER" | "FLOAT" | "BOOLEAN" | "DATE" | "DATETIME"
RELATION_TYPE := "HAS_MANY" | "HAS_ONE" | "BELONGS_TO"
HTTP_METHOD   := "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
MODEL_NAME    := PascalCase identifier
FIELD_NAME    := snake_case identifier
PATH          := "/" segment ("/" segment)*
segment       := [A-Za-z0-9][A-Za-z0-9_-]* | "{" snake_case "}"
```

## PROJECT

```text
PROJECT BlogAPI
```

Exactly one project declaration is required. It names the generated project.

## TARGET

```text
TARGET FASTAPI
```

Selects the generator: `PHP` (default), `FASTAPI` or `NESTJS`. The CLI `--target` option
overrides it. Other names are rejected.

## DATABASE

```text
DATABASE POSTGRESQL
```

`MYSQL`, `POSTGRESQL` or `SQLITE`. It sets the default connection of the generated project
and the database service in `docker-compose.yml`. Without a declaration the project uses
SQLite (and diagnostic `DB001` warns). Generated projects can still switch databases with
the `DB_CONNECTION` environment variable.

## AUTH

```text
AUTH JWT
```

Generates real token authentication: `POST /register`, `POST /login`, `GET /me`, bcrypt
password hashing and HS256 tokens. The account model is `User`; it is created if missing,
and `email` (unique) and `password` (secret) are added if not declared. A declared
`User.email` or `User.password` must be a required `STRING`. `AUTH SESSION` is not
implemented and is rejected; declaring two strategies raises diagnostic error `AUTH002`,
which blocks generation.

## MODEL

```text
MODEL User
    name STRING
    email STRING UNIQUE
    bio TEXT OPTIONAL
```

| Type | Stored as | JSON |
| --- | --- | --- |
| `STRING` | VARCHAR(255) | string, at most 255 characters |
| `TEXT` | TEXT | string |
| `INTEGER` | INTEGER | integer |
| `FLOAT` | DOUBLE / REAL | number |
| `BOOLEAN` | BOOLEAN | `true` / `false` |
| `DATE` | DATE | `"2026-01-31"` |
| `DATETIME` | DATETIME / TIMESTAMP (UTC) | `"2026-01-31T09:30:00Z"`; offsets such as `+05:30` are converted to UTC, values without an offset are UTC |

Modifiers:

- `UNIQUE`: duplicates are rejected with 409 and enforced by a unique constraint.
- `OPTIONAL`: the field may be omitted or `null`. Fields are required otherwise.

Rules: model names are PascalCase, field names snake_case, field names are unique per
model, and `id`, `created_at` and `updated_at` are generated automatically and cannot be
declared.

## RELATION

```text
RELATION User HAS_MANY Post
RELATION Post BELONGS_TO User
RELATION User HAS_ONE Profile
```

Each relation creates one foreign key column on the child (`posts.user_id`) that is required
and references the parent. `HAS_ONE` makes the column unique. Declaring both directions of
the same relationship produces a single column. A child must not declare a field with the
foreign key's name. Relationships must not form ownership cycles.

Foreign keys drive migration order, reference checks (422 for a missing parent), delete
protection (409 while children exist), nested list routes and ownership: a model that
references `User` is owned by that user, who alone may change it on protected routes (see
[GENERATED_API.md](GENERATED_API.md)).

## ROUTE

```text
ROUTE GET /posts
ROUTE GET /posts/{id}
ROUTE PATCH /posts/{id}
ROUTE GET /users/{id}/posts PROTECTED
ROUTE DELETE /posts/{id} PUBLIC
```

The route shape decides the operation (list, create, read, replace, update, delete, nested
list); anything else becomes a custom route returning 501 until implemented. `/`,
`/health`, `/routes`, `/openapi.json` and `/docs` are reserved. Path parameters are
snake_case and unique within a
path. `PROTECTED` requires `AUTH JWT`. `POST /register` and `GET /me` require `AUTH JWT`;
with it they are added automatically. See [GENERATED_API.md](GENERATED_API.md) for the
full mapping and the default access policy.

## VALIDATE

```text
VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN 8
VALIDATE Post.title REQUIRED MAX 120
VALIDATE rating MIN 0 MAX 5
```

| Rule | Meaning |
| --- | --- |
| `REQUIRED` | the value must be present and, for text, not blank |
| `EMAIL` | the value must be an email address (text fields only) |
| `MIN n` | minimum length for text, minimum value for numbers |
| `MAX n` | maximum length for text, maximum value for numbers |

An unscoped field name applies to every model that declares that field (and to the auth
credentials). `Model.field` applies to one model. `MIN` without a number means `MIN 6`, for
compatibility with earlier versions. The validator rejects unknown fields, rules that do not
fit the field type, `MIN` greater than `MAX`, `MAX` above 255 on `STRING` (use `TEXT`),
`MAX` above 72 on the password, `REQUIRED` on an `OPTIONAL` field, and duplicate
validations for the same field.

## PROFILE and USE

```text
PROFILE ECOMMERCE
USE payment.razorpay
```

`PROFILE` composes profile metadata from `semarc/profiles/*.profile`, including inherited profiles
and their modules. `USE` resolves stdlib modules from `semarc/stdlib/**/module.yaml`, including their
`depends`, `requires` and `conflicts` rules. Resolved profiles and modules appear in the
architecture report and the generator manifest. Unknown `USE` names are kept as metadata.

## Complete Example

```text
PROJECT BlogAPI

TARGET NESTJS

DATABASE MYSQL

AUTH JWT

MODEL User
    name STRING
    email STRING UNIQUE
    password STRING

MODEL Post
    title STRING
    body TEXT
    published BOOLEAN OPTIONAL

RELATION User HAS_MANY Post

VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN 8
VALIDATE Post.title REQUIRED MAX 120

ROUTE GET /posts
ROUTE GET /posts/{id}
ROUTE POST /posts
ROUTE PATCH /posts/{id}
ROUTE DELETE /posts/{id}
ROUTE GET /users/{id}/posts
```

## Not Supported

Free-form instructions are rejected:

```text
Create a blog API with users and posts
```

Not yet expressible: many-to-many relations without an explicit join model, and roles and
permissions.

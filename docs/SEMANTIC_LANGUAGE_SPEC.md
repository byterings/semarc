# Semantic Language Specification

The SEMARC semantic language is a strict declarative architecture language. It describes what backend architecture should exist, not how code should execute line by line.

## Design Properties

The language is:

- declarative
- semantic
- architecture-oriented
- deterministic
- whitespace-light, with indentation only used for model fields

The language is not:

- procedural programming
- natural language
- prompt syntax
- framework syntax

## Supported Keywords

```text
PROJECT
TARGET
DATABASE
AUTH
MODEL
RELATION
ROUTE
VALIDATE
```

## Lexical Rules

Source is processed line by line.

Blank lines are ignored.

Keywords are uppercase.

Model fields are indented under a `MODEL` declaration.

## Grammar Sketch

```text
program       := statement*
statement     := project | target | database | auth | model | relation | route | validate

project       := "PROJECT" IDENTIFIER
target        := "TARGET" IDENTIFIER
database      := "DATABASE" IDENTIFIER
auth          := "AUTH" IDENTIFIER
model         := "MODEL" IDENTIFIER field*
field         := INDENT IDENTIFIER TYPE
relation      := "RELATION" IDENTIFIER RELATION_TYPE IDENTIFIER
route         := "ROUTE" HTTP_METHOD PATH
validate      := "VALIDATE" IDENTIFIER VALIDATION_RULE+
```

## PROJECT

Declares project identity.

```text
PROJECT BlogAPI
```

Semantic meaning: creates the root project identity used by architecture planning and target generators.

Constraints:

- exactly one project declaration is expected
- project name must be an identifier

## TARGET

Selects target profile.

```text
TARGET PHP
TARGET FASTAPI
```

Semantic meaning: selects generator and implementation strategy.

If omitted, SEMARC defaults to PHP.

## DATABASE

Declares database architecture intent.

```text
DATABASE MYSQL
```

Semantic meaning: backend requires database configuration and migration planning.

Current supported value:

```text
MYSQL
```

## AUTH

Declares authentication architecture.

```text
AUTH JWT
```

Semantic meaning: token-based authentication is required.

Current supported value:

```text
JWT
```

Architecture expansion may produce:

- auth controller/router
- token service
- password hasher
- auth middleware
- validator

## MODEL

Declares semantic data model.

```text
MODEL User
    name STRING
    email STRING
    password STRING
```

Supported field types:

```text
STRING
TEXT
INTEGER
BOOLEAN
FLOAT
```

Semantic meaning: model, repository, schema, migration table, and target-specific model files may be generated.

## RELATION

Declares semantic relationship between models.

```text
RELATION User HAS_MANY Post
RELATION Post BELONGS_TO User
RELATION User HAS_ONE Profile
```

Supported relationship types:

```text
HAS_MANY
BELONGS_TO
HAS_ONE
```

Semantic meaning: relationship engine generates foreign keys, repository dependencies, migration metadata, and ORM relationship metadata.

## ROUTE

Declares HTTP endpoint.

```text
ROUTE POST /login
ROUTE GET /users
```

Supported methods:

```text
GET
POST
PUT
PATCH
DELETE
```

Semantic meaning: route generation and route-to-handler mapping.

## VALIDATE

Declares input validation intent.

```text
VALIDATE email REQUIRED EMAIL
VALIDATE password REQUIRED MIN
```

Supported rules:

```text
REQUIRED
EMAIL
MIN
```

Semantic meaning: target generator emits validation helpers and request validation logic.

## Complete Example

```text
PROJECT BlogAPI

TARGET FASTAPI

DATABASE MYSQL

AUTH JWT

MODEL User
    name STRING
    email STRING

MODEL Post
    title STRING
    content STRING

RELATION User HAS_MANY Post

ROUTE POST /login
ROUTE GET /posts
```

## Constraints

SEMARC intentionally rejects free-form instructions.

Invalid:

```text
Create a blog API with users and posts
```

Valid:

```text
MODEL User
MODEL Post
RELATION User HAS_MANY Post
```

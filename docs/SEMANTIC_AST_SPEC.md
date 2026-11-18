# Semantic AST Specification

The Semantic AST is the compiler representation of architecture meaning.

It is not a syntax tree for PHP, Python, SQL, or any framework. It stores semantic intent only.

## AST Boundary

AST nodes may contain:

- semantic names
- semantic types
- source locations
- metadata
- child semantic nodes

AST nodes must not contain:

- generated code
- target-specific imports
- file paths
- template names
- framework classes

## Root Node

### ArchitectureNode

Represents the complete semantic architecture program.

Fields:

- `project`
- `target`
- `database`
- `auth`
- `models`
- `routes`
- `relations`
- `validations`
- `profiles`
- `packages`
- `location`
- `metadata`

Relationship:

```text
ArchitectureNode
    +-- ProjectNode
    +-- TargetNode
    +-- DatabaseNode
    +-- AuthNode
    +-- ModelNode[]
    |       +-- FieldNode[]
    +-- RouteNode[]
    +-- RelationNode[]
    +-- ValidationNode[]
    +-- ProfileNode[]
    +-- PackageNode[]
```

## Node Metadata

Nodes support source metadata for debugging and validation.

```text
location:
    line
    column

metadata:
    arbitrary semantic metadata
```

Source locations are used for readable errors:

```text
[Semantic Error]
Undefined model: Post
Line: 18
```

## Nodes

### ProjectNode

Semantic project identity.

Fields:

- `name`

Example:

```text
PROJECT BlogAPI
```

### TargetNode

Requested target profile.

Fields:

- `name`

Example:

```text
TARGET FASTAPI
```

### ProfileNode

Profile selection.

Fields:

- `name`

Example:

```text
PROFILE Ecommerce
```

Profiles are composed by `ProfilePass` (with inheritance) and their modules are resolved.

### PackageNode

Stdlib module selection from `USE`.

Fields:

- `name`

Example:

```text
USE payment.razorpay
```

Known modules are resolved with their dependencies and constraints; unknown names stay metadata.

### DatabaseNode

Database architecture intent.

Fields:

- `engine`

Example:

```text
DATABASE MYSQL
```

### AuthNode

Authentication intent.

Fields:

- `strategy`

Example:

```text
AUTH JWT
```

### ModelNode

Semantic domain model.

Fields:

- `name`
- `fields`

Example:

```text
MODEL User
    email STRING
```

### FieldNode

Semantic model field.

Fields:

- `name`
- `field_type`
- `modifiers`: `UNIQUE` and/or `OPTIONAL`

Example:

```text
    email STRING UNIQUE
```

### RelationNode

Semantic relationship between two models.

Fields:

- `source_model`
- `relation_type`
- `target_model`

Example:

```text
RELATION User HAS_MANY Post
```

### RouteNode

Semantic HTTP endpoint.

Fields:

- `method`
- `path`, which may contain `{param}` segments
- `access`: `PUBLIC`, `PROTECTED` or `None` (default policy)

Example:

```text
ROUTE DELETE /posts/{id} PUBLIC
```

### ValidationNode

Input validation intent.

Fields:

- `field_name`
- `rules`: `REQUIRED`, `EMAIL`, `MIN`, `MAX`
- `model_name`: set for `Model.field` targets, otherwise `None`
- `parameters`: numeric values, for example `{"MIN": 8, "MAX": 64}`

Example:

```text
VALIDATE Post.title REQUIRED MAX 120
```

## AST Construction

`ast/ast_builder.py` centralizes node construction. The parser delegates node creation to the builder so parser code remains grammar-focused.

## Debug Representation

Nodes expose debug data with semantic fields, location, and metadata. Debug output is used by:

- `--debug`
- tests
- future visualization tools

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
- `path`

Example:

```text
ROUTE POST /login
```

### ValidationNode

Input validation intent.

Fields:

- `field_name`
- `rules`

Example:

```text
VALIDATE email REQUIRED EMAIL
```

## AST Construction

`ast/ast_builder.py` centralizes node construction. The parser delegates node creation to the builder so parser code remains grammar-focused.

## Debug Representation

Nodes expose debug data with semantic fields, location, and metadata. Debug output is used by:

- `--debug`
- tests
- future visualization tools

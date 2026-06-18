# Relationship Engine

The relationship engine makes SEMARC relationship-aware. It converts semantic relationship declarations into graph data, foreign keys, repository dependency metadata, and migration metadata.

## Input

Semantic relations:

```text
RELATION User HAS_MANY Post
RELATION Post BELONGS_TO User
RELATION User HAS_ONE Profile
```

AST nodes:

```text
RelationNode(source_model, relation_type, target_model)
```

## Supported Relationships

```text
HAS_MANY
BELONGS_TO
HAS_ONE
```

## Example Expansion

Input:

```text
MODEL User
    name STRING

MODEL Post
    title STRING

RELATION User HAS_MANY Post
```

Relationship engine output:

```json
{
  "relationships": [
    {"source": "User", "type": "HAS_MANY", "target": "Post"}
  ],
  "foreign_keys": [
    {
      "table": "posts",
      "column": "user_id",
      "references_table": "users",
      "references_column": "id"
    }
  ]
}
```

## Generated Architecture Effects

`User HAS_MANY Post` should synthesize:

- `posts.user_id` foreign key
- `UserRepository` dependency on `PostRepository`
- ORM relationship on `User`
- inverse ORM relationship on `Post`
- migration metadata for `posts`

## Relationship Graph

```text
User
    HAS_MANY -> Post

Post
    []
```

The graph is used for debugging and future architecture analysis.

## Foreign Key Rules

For `A HAS_MANY B`:

```text
B table receives a_id
```

For `B BELONGS_TO A`:

```text
B table receives a_id
```

For `A HAS_ONE B`:

```text
B table receives a_id
```

## Validation Rules

The validator detects:

- undefined source model
- undefined target model
- duplicate relationships
- invalid relationship type
- circular ownership relationships

Example:

```text
[Semantic Error]
Undefined model: Post
Line: 18
```

## Target Mapping

Relationship engine output remains target-neutral.

PHP generator maps relationships to metadata comments and migration foreign keys:

```php
// Relation metadata: User HAS_MANY Post
```

FastAPI generator maps relationships to schema/table metadata and migration foreign keys:

```python
# Relation metadata: User HAS_MANY Post
```

Runtime relationship helper methods are not emitted until target runtime support exists.

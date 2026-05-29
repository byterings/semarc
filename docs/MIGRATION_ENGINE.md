# Migration Engine

The migration engine is responsible for converting semantic models and relationships into target-neutral migration metadata, then letting target generators map that metadata into concrete migration files.

## Input

Models:

```text
MODEL User
    name STRING

MODEL Post
    title STRING
```

Relationships:

```text
RELATION User HAS_MANY Post
```

## Migration Plan

The relationship engine creates migration metadata:

```json
{
  "tables": [
    {
      "model": "Post",
      "table": "posts",
      "fields": [
        {"name": "title", "type": "STRING"}
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
  ],
  "foreign_keys": []
}
```

## SQL Type Mapping

Semantic types are target-neutral.

Target generators map them:

```text
STRING  -> VARCHAR(255) or String
TEXT    -> TEXT or String
INTEGER -> INT or Integer
BOOLEAN -> BOOLEAN or Integer
FLOAT   -> FLOAT or Integer
```

## PHP Migration Output

PHP target generates:

```text
output/migrations/create_users_table.sql
output/migrations/CreateUsersTable.php
```

SQL example:

```sql
CREATE TABLE posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    user_id INT NOT NULL,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## FastAPI Migration Output

FastAPI target generates SQLAlchemy table metadata:

```text
output/migrations/create_posts_table.py
```

Example:

```python
posts = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String),
    Column("user_id", Integer, ForeignKey("users.id")),
)
```

## Boundary

Migration metadata is produced before target generation. Target generators render it only.

The migration engine must not contain PHP or FastAPI syntax.

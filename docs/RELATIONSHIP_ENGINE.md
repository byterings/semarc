# Relationship Engine

The relationship engine (`semarc/architecture/relationship_engine.py`) turns semantic relations
into a relationship graph, foreign keys and migration metadata.

## Supported Relationships

```text
RELATION User HAS_MANY Post
RELATION Post BELONGS_TO User
RELATION User HAS_ONE Profile
```

## Foreign Key Rules

| Declaration | Column |
| --- | --- |
| `A HAS_MANY B` | `b_table.a_id` |
| `B BELONGS_TO A` | `b_table.a_id` |
| `A HAS_ONE B` | `b_table.a_id`, unique |

Declaring both directions (`User HAS_MANY Post` and `Post BELONGS_TO User`) produces one
column. Foreign key columns are required.

## Validation

The validator rejects undefined models, duplicate relationships, invalid relation types,
circular ownership and child fields that collide with a generated foreign key column.

## Effects on the Generated API

The resource planner records each foreign key twice in the IR model specs:

- as a `reference` on the child, used for input validation (the parent must exist, else
  422), unique checks for `HAS_ONE` (409) and token ownership when the parent is the auth
  model;
- as a `dependent` on the parent, used to refuse deletes while children exist (409).

A route shaped `GET /<parents>/{id}/<children>` lists the children of one parent when the
child references the parent.

The dependency graph records the child entity depending on the parent and the child
service depending on the parent repository.

## Target Mapping

Relationship metadata stays target-neutral. Targets render foreign key columns and
constraints in migrations, reference checks in services and relation comments in models.
ORM relationship objects and lazy-loading helpers are intentionally not generated; nested
data is reached through the nested list routes.

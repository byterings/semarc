# Architecture IR Specification

Architecture IR is SEMARC's framework-independent internal representation. It is the
bridge between semantic meaning and target generation: every decision about what the
generated API does is recorded here, and generators only translate it.

## IR Boundary

IR may contain components, models, fields and their rules, relationships, foreign keys,
migration metadata, route operations, access policy, auth settings, profile, package and
module metadata, target profile metadata and dependency graph data.

IR must not contain PHP, Python or TypeScript code, framework names in data values, file
paths or template names. `ContractValidator.validate_ir` scans for leakage markers.

## Top-Level Shape

```json
{
  "project": "BlogAPI",
  "target": "FASTAPI",
  "target_profile": {"target": "FASTAPI", "generator": "fastapi", "framework": "fastapi", "auth_strategy": "jwt_hs256", "repository_strategy": "sqlalchemy"},
  "config": {"database": {"engine": "POSTGRESQL"}},
  "auth": {},
  "models": [],
  "routes": [],
  "repositories": [],
  "controllers": [],
  "services": [],
  "middlewares": [],
  "validators": [],
  "relationships": [],
  "foreign_keys": [],
  "migrations": {"tables": [], "foreign_keys": []},
  "profiles": [],
  "packages": [],
  "modules": [],
  "dependency_graph": {},
  "relationship_graph": {}
}
```

## auth

`null` without `AUTH JWT`, otherwise:

```json
{
  "strategy": "JWT",
  "model": "User",
  "identity_field": "email",
  "secret_field": "password",
  "token_ttl_seconds": 3600,
  "implicit_model": false
}
```

`implicit_model` is true when the specification did not declare `User` and the auth layer
created it.

## models

```json
{
  "name": "Post",
  "table": "posts",
  "resource": "posts",
  "origin": "declared",
  "fields": [
    {
      "name": "title",
      "type": "STRING",
      "required": true,
      "unique": false,
      "secret": false,
      "rules": {"required": true, "not_empty": true, "email": false, "min": null, "max": 120}
    }
  ],
  "relations": [{"source": "User", "type": "HAS_MANY", "target": "Post"}],
  "foreign_keys": [{"table": "posts", "column": "user_id", "references_table": "users", "references_column": "id", "source_model": "User", "target_model": "Post", "unique": false}],
  "references": [{"column": "user_id", "model": "User", "table": "users", "unique": false, "owner": true}],
  "dependents": []
}
```

- `origin` is `declared` or `auth` (created by `AUTH JWT`).
- `rules` merge `OPTIONAL` and every applicable `VALIDATE`. Generators add the 255
  character `STRING` limit and the 72 character secret limit
  (`generator/utils/resource_views.py`).
- `references` are this model's foreign key columns; `owner` marks a reference to the auth
  model, which protected creates fill from the token.
- `dependents` are tables whose rows reference this model; deletes are refused while they exist.

## routes

```json
{
  "method": "GET",
  "path": "/users/{id}/posts",
  "origin": "declared",
  "access": "public",
  "parameters": ["id"],
  "operation": {"kind": "list_related", "model": "Post", "parent_model": "User", "parameter": "id", "foreign_key": "user_id"},
  "handler": {"type": "controller", "component": "PostController", "action": "list_related"}
}
```

- `origin`: `declared`, `completed` (the default `GET /<resource>` per model) or `auth`.
- `access`: `public` or `protected`, after applying the access policy.
- `operation.kind`: `list`, `read`, `create`, `replace`, `update`, `delete`, `list_related`,
  `auth_register`, `auth_login`, `auth_me` or `custom`.
- `handler` is kept for compatibility with the generation contract and debug output. Custom
  routes without a model use `{"type": "todo", "action": "custom"}`.

The IR route list is complete: generators must not add or infer routes.

## migrations

```json
{
  "tables": [
    {
      "model": "Post",
      "table": "posts",
      "sequence": 2,
      "fields": [{"name": "title", "type": "STRING", "required": true, "unique": false}],
      "foreign_keys": [{"table": "posts", "column": "user_id", "references_table": "users", "references_column": "id", "unique": false}]
    }
  ],
  "foreign_keys": []
}
```

The optimizer orders tables so that referenced tables come first and assigns `sequence`.
Targets render this as PDO table definitions (PHP), Alembic revisions (FastAPI) or TypeORM
migrations (NestJS). `id`, `created_at` and `updated_at` are implied.

## Components

`repositories`, `controllers`, `services`, `middlewares` and `validators` describe
architecture components for the dependency graph, debug output and the generation contract.
Repositories have `type: "sql"`.

## Determinism

After optimization, models and repositories are sorted by name, relationships by source,
type and target, and migration tables in dependency order with name as tie breaker.
Duplicate components are removed. The same source always produces the same IR.

## Contract Validation

`compiler/contracts.py` validates required keys, model and route shapes, repository metadata
and target leakage before generation. `architecture/contracts/` then builds the
framework-neutral generation contract from the IR and validates target capabilities and the
generated artifacts.

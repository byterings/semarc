# Dependency Graph

The dependency graph tracks architecture relationships between generated components.

It is not an import graph. It is a semantic architecture graph.

## Purpose

The graph answers questions such as:

- what does `AuthMiddleware` require?
- what components depend on `DatabaseConfig`?
- is there a dependency cycle?
- what order can components be reasoned about?

## API

Core operations:

```python
graph.add_node("AuthMiddleware")
graph.add_dependency("AuthMiddleware", "TokenService")
graph.validate()
graph.traverse()
```

## Nodes

Nodes represent architecture components:

```text
AuthController
AuthMiddleware
TokenService
PasswordHasher
Validator
UserRepository
DatabaseConfig
Route:POST:/login
```

## Edges

Edges represent semantic dependencies:

```text
AuthMiddleware -> TokenService
TokenService -> Validator
UserRepository -> DatabaseConfig
Route:POST:/login -> AuthController
```

## Example

```text
AuthMiddleware
    |
    v
TokenService
    |
    v
Validator
```

Debug shape:

```json
{
  "nodes": ["AuthMiddleware", "TokenService", "Validator"],
  "dependencies": {
    "AuthMiddleware": ["TokenService"],
    "TokenService": ["Validator"],
    "Validator": []
  },
  "order": ["Validator", "TokenService", "AuthMiddleware"]
}
```

## Validation

Dependency graph validation checks:

- dependency target exists
- duplicate dependencies
- cycle detection during traversal

Diagnostics report:

- orphan nodes
- root nodes
- node count
- dependency count
- duplicate dependency entries

## Boundary

The dependency graph does not generate files.

It should not contain:

- import statements
- template names
- file paths
- framework code

Generators may use graph data for ordering later, but current generation mostly uses IR component lists.

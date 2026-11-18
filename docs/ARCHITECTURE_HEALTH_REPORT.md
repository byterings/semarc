# Architecture Health Report

This report records the stabilization audit for SEMARC's compiler architecture.

> Status update (v0.14.0): the remaining risks below were addressed. Repositories persist to
> real databases, migrations are ordered topologically by foreign keys, route semantics moved
> into the architecture layer (`resource_planner.py`), output cleanup moved into
> `generator/output_directory.py`, and target snapshots plus runtime scenarios cover all
> three targets. The original audit is kept below for history.

## Scope

This pass focused on:

- IR purity
- generator boundary enforcement
- compiler pass isolation
- dependency graph validation
- template normalization
- target contamination checks
- architecture contracts
- stability tests

No major semantic language features were added.

## Resolved Issues

### IR Route Handler Normalization

Previous route handlers used target-shaped terms:

```json
{
  "class": "AuthController",
  "method": "login"
}
```

This was normalized to target-neutral architecture terms:

```json
{
  "component": "AuthController",
  "action": "login"
}
```

PHP now maps `component/action` to class/method syntax inside the PHP generator only.

### Contract Validation Added

Added `compiler/contracts.py` and `compiler/passes/contract_pass.py`.

Contracts now validate:

- AST structure
- required IR keys
- model IR shape
- route handler shape
- repository metadata
- generated component metadata
- target-specific leakage markers

### Dependency Graph Diagnostics Strengthened

`DependencyGraph` now tracks:

- duplicate dependencies
- orphan nodes
- root nodes
- node count
- dependency count

Validation now detects:

- missing dependency references
- duplicate dependencies
- circular dependencies

### Dead Compatibility Files Removed

Removed inactive files:

- `compiler/passes/parse_pass.py`
- `templates/fastapi/routes.tpl`
- `templates/fastapi/validator.tpl`
- `templates/php/controller.tpl`

This reduces pass/template confusion and makes active paths clearer.

### Debug Validation Improved

Debug mode now prints:

```text
[IR Validation]
PASS: No target-specific leakage detected

[Dependency Graph]
Nodes: ...
Dependencies: ...
Orphans: ...
Duplicate dependencies: ...
```

### Stability Tests Added

Expanded tests for:

- IR purity
- duplicate dependency detection
- target independence
- pass order
- deterministic generation

## Current Architecture Health

### IR Purity

Status: passing.

IR no longer contains PHP-specific route handler terms. Target profile metadata remains explicitly allowed as target selection data.

### Generator Boundaries

Status: acceptable.

Generators still perform target mapping and template rendering. Relationship inference and migration planning remain in architecture/compiler layers.

Remaining risk: some target mappers still contain small naming conventions and route mapping assumptions. These are target mapping concerns, but they should stay under review.

### Compiler Pass Isolation

Status: improved.

Pass order is now tested. Contract checks are explicit between parsing, IR building, and generation.

### Dependency Graph

Status: improved.

Diagnostics are richer. Orphan nodes are reported, not failed, because route or standalone components can be valid roots in the current architecture.

### Template Normalization

Status: improved.

Unused templates were removed. Active templates now better reflect current generator paths.

## Remaining Risks

- FastAPI router generation is still concentrated in `auth_router.tpl`; future route expansion should split route templates by semantic route type.
- Repository templates remain prototype-level and in-memory.
- Migration ordering is deterministic but not yet dependency-topologically sorted.
- Contract validation is structural, not a full schema system.
- Output cleanup is target-aware but should eventually move into a shared artifact manager.

## Recommendations

1. Add a formal IR schema module if IR continues to grow.
2. Add topological migration ordering based on foreign keys.
3. Move generated artifact cleanup into a shared generator utility.
4. Add target fixture snapshots for PHP and FastAPI.
5. Add route mapping rules to architecture layer if route semantics become richer.
6. Keep all new semantic decisions outside generators.

## Verification

Executed during stabilization:

```bash
python3 -m unittest discover -s tests
python3 -m compileall main.py architecture compiler generator lexer parser validator tests ast_loader.py
python3 main.py examples/blog_fastapi.sem --target fastapi --debug
python3 main.py examples/blog_fastapi.sem --target php
php -l output/routes.php
php -l output/models/User.php
php -l output/models/Post.php
php -l output/repositories/UserRepository.php
```

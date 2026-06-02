# Roadmap

SEMARC is a prototype moving toward a well-specified semantic backend compiler.

## v0.1: Semantic Parsing and Backend Generation

Status: complete.

- semantic source files
- lexer
- parser
- semantic AST
- PHP backend generation
- basic routes, models, auth, config

## v0.2: Compiler Architecture

Status: complete.

- semantic validator
- architecture expansion
- Architecture IR
- modular generators
- template-based generation
- debug output

## v0.3: Multi-Target Generation

Status: complete.

- target profile system
- PHP target
- FastAPI target
- target override via CLI
- FastAPI mappers
- target-specific output structures

## v0.4.0: Semantic Package System Foundation

Status: current.

- semantic package architecture
- profile architecture
- company standards foundation
- reusable semantic module placeholders
- stdlib metadata directories
- profile and package registries
- optional `PROFILE` and `USE` parser hooks
- backward-compatible AST and IR metadata

## v0.4.x: Relationship-Aware Compiler

Status: complete.

- `RELATION` syntax
- `RelationNode`
- relationship validation
- relationship graph
- foreign key planning
- migration metadata
- PHP migrations
- FastAPI SQLAlchemy table migrations
- relationship-aware repositories
- ORM relationship generation

## v0.5.0: Stdlib Foundation

Status: complete.

- recursive stdlib module discovery
- `ModuleDefinition`
- `ModuleRegistry`
- `StdlibLoader`
- `USE` validation against stdlib modules
- stdlib diagnostics `SEM5001` through `SEM5004`
- architecture report module metadata

## v0.6.0: Module Dependency Resolution

Status: current.

- optional `depends` entries in `module.yaml`
- recursive module dependency resolution
- deterministic module ordering
- duplicate dependency elimination
- circular dependency diagnostic `SEM6001`
- missing dependency diagnostic `SEM6002`
- invalid dependency schema diagnostic `SEM6003`

## v0.7: Optimization Engine

Status: planned.

- duplicate component elimination
- migration ordering
- middleware ordering
- dependency simplification
- dead route detection

## v0.8: Semantic Standard Library

Status: planned.

- reusable auth modules
- reusable validation modules
- database capability modules
- relationship modules
- target compatibility metadata

## v0.9: Advanced Architecture Synthesis

Status: planned.

- richer route-to-controller mapping
- command/query separation
- policies and authorization rules
- service dependency planning
- richer repository strategies

## v1.0: Production Target Profiles

Status: planned.

- Laravel profile
- Node profile
- PostgreSQL support
- Docker output
- environment configuration

## Long-Term

- frontend generation
- infrastructure synthesis
- workflow systems
- semantic deployment

Current focus remains deterministic semantic backend compilation.

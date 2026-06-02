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

Status: complete.

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

Status: complete.

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

## v0.8.0: Profile Composition

Status: complete.

- profile module composition
- inherited profile module resolution
- deterministic duplicate elimination
- circular profile detection
- profile-aware module loading

## v0.9.0: Architecture Intelligence

Status: complete.

- deterministic architecture analyzer
- read-only architecture analysis pass
- public route authentication warnings
- payment and audit pairing recommendations
- unused model warnings
- ecommerce SQLite recommendations
- auth-without-protected-route recommendations
- architecture report analysis section

## v0.10.0: NestJS Generator

Status: current.

- `TARGET NESTJS`
- NestJS target profile
- TypeScript project structure generation
- model class generation
- service skeleton generation
- controller skeleton generation
- placeholder auth guard scaffolding
- app module registration
- PHP and FastAPI compatibility preserved

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

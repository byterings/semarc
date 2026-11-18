# Changelog

All notable changes to SEMARC are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/). Before 1.0, minor versions may change the
language; such changes are listed under **Changed**.

## [Unreleased]

### Added
- MIT license, security policy, code of conduct, issue and pull request templates.
- Installable package: `pip install semarc` / `pipx install semarc`, `python -m semarc`.
- `semarc init` with `blank`, `blog` and `shop` starters; `docs/GETTING_STARTED.md`.
- Release workflow publishing to PyPI through trusted publishing; `docs/RELEASING.md`.
- CI runs the compiler tests on Linux, macOS and Windows with Python 3.11 and 3.13 and
  smoke-tests the installed wheel.
- `scripts/project_tests.py` runs each generated project's own test suite in Docker.

### Changed
- All compiler code moved into the `semarc` package (`semarc.compiler`, `semarc.generator`,
  ...). `python3 main.py` keeps working in a checkout.
- Generated files always use LF line endings and recorded paths use forward slashes, so
  output is identical on every operating system.

## [0.14.0] - 2026-11-18

Generated projects became runnable, database-backed APIs.

### Added
- Language: field modifiers `UNIQUE` and `OPTIONAL`; `DATE` and `DATETIME` types; route path
  parameters (`/posts/{id}`); `PUBLIC` / `PROTECTED` route access; `VALIDATE MIN n` /
  `MAX n`; model-scoped validation (`VALIDATE Post.title ...`).
- Resource planning in the architecture layer: route operations, access policy, the auth
  model, ownership, references, dependents, filters and sorting recorded in the IR.
- PHP, FastAPI and NestJS generate working APIs for MySQL, PostgreSQL and SQLite: CRUD and
  nested list routes, JWT authentication with bcrypt, owner-only writes, validation,
  consistent errors, pagination, equality filters and sorting, CORS, rate-limited login,
  migrations, OpenAPI 3.1 with Swagger UI, Docker and a test runner.
- `api_scenario.json` behaviour contract in every project, replayed by each target's tests
  and by `scripts/e2e_runtime.py` against live Docker stacks.
- `semarc` command (`build`, `check`, `targets`, `version`), `--output` and `--force`.
- Migration ordering by foreign keys and component de-duplication.
- GitHub Actions CI.

### Changed
- Unimplemented targets (`LARAVEL`, `NODE`) and `AUTH SESSION` are rejected instead of
  silently generating PHP or no authentication.
- Diagnostic errors block generation.
- Keywords are case sensitive, so models such as `Profile` are valid.

### Fixed
- Declaring both directions of a relationship created a dependency cycle and a duplicate
  foreign key.
- The output directory kept stale files from previous runs.

## [0.13.0]

Project experience endpoints (`/`, `/health`, `/routes`), shared pluralization, target
manifests and registry-driven target selection.

## [0.12.0]

Project template foundation (README, environment, Docker, manifest per target) and the
framework-neutral generation contract.

## [0.11.0] and earlier

Release hardening and golden tests (0.11), NestJS generator (0.10), architecture
intelligence (0.9), profile composition (0.8), module constraints and dependency resolution
(0.6–0.7), stdlib modules (0.5), relationship-aware compilation and the package system (0.4),
multi-target generation (0.3), compiler architecture (0.2) and the first semantic parser and
PHP backend generation (0.1).

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
- Roles: `USE auth.roles` and `ROUTE ... ROLE admin editor`, a managed `role` field,
  `BOOTSTRAP_ADMIN_EMAIL`, `PUT /users/{id}/role`, and admin access to records owned by others.
- `RELATION User ...` works when `User` is created by `AUTH JWT` rather than declared.
- Refresh tokens (rotating, hashed, `JWT_REFRESH_TTL`), `POST /token/refresh`, `POST /logout`
  and `POST /me/password` for every `AUTH JWT` project.
- Migrations support `ON DELETE CASCADE` for infrastructure tables.
- Password reset (`USE auth.password_reset`: `POST /password/forgot`, `POST /password/reset`) and
  email verification (`USE auth.email_verification`: `email_verified_at`, `POST /email/verify`,
  `POST /email/resend`) with single-use hashed tokens.
- Plain-text email in every target (`MAIL_DRIVER` smtp/log/memory, `MAIL_*` settings, `APP_URL`
  links) and a Mailpit inbox in the generated `docker-compose.yml`.
- `api_scenario.json` mail steps, replayed by every runner (Mailpit in `scripts/e2e_runtime.py`).
- Sign in with Google and GitHub (`USE auth.oauth.google`, `USE auth.oauth.github`): signed
  state, server-side code exchange, accounts linked by verified email in `oauth_accounts`.
- `AUTH SESSION`: server-side sessions in an HttpOnly cookie with a CSRF header, the same
  routes and modules as `AUTH JWT`, and credentialed CORS for listed origins.
- `TRUSTED_PROXIES`: the rate limiter uses `X-Forwarded-For` only from trusted proxies.
- `USE cache.redis` keeps rate limit counters in Redis (with a local fallback) and adds
  Redis to `docker-compose.yml`.
- `api_scenario.json` `env` settings and `external` steps; `scripts/oauth_mock.py` provides a
  deterministic OAuth provider for `scripts/e2e_runtime.py`.

### Changed
- `AUTH SESSION` is no longer rejected.
- All compiler code moved into the `semarc` package (`semarc.compiler`, `semarc.generator`,
  ...). `python3 main.py` keeps working in a checkout.
- Generated PHP projects run on nginx + php-fpm in Docker (production `php.ini`, OPcache)
  instead of PHP's built-in development server.
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

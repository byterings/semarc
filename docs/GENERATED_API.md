# Generated API Contract

Every target (PHP, FastAPI, NestJS) generates an API with the same observable behaviour.
The behaviour is decided in the architecture layer (`semarc/architecture/resource_planner.py`)
and expressed in the Architecture IR; generators only translate it.

The contract is verified by `api_scenario.json`, which SEMARC writes into every generated
project (see [Verification](#verification)).

## Built-in endpoints

| Method | Path | Response |
| --- | --- | --- |
| GET | `/` | HTML overview of the project, models and routes |
| GET | `/health` | `{"status": "ok", "project": "...", "database": "ok"}`, or 503 with `database: "unavailable"` |
| GET | `/routes` | `{"routes": ["GET /", ...]}` |

| GET | `/openapi.json` | OpenAPI 3.1 document of the whole API |
| GET | `/docs` | Swagger UI for the document |

These paths are reserved and cannot be declared with `ROUTE`.

The OpenAPI document is generated once from the IR (`semarc/generator/utils/openapi.py`) and served
unchanged by every target, including FastAPI, whose own schema generation is replaced so the
documented envelopes, errors, filters and security match the behaviour. It lists request and
response schemas with their validation rules, list parameters, bearer security on protected
operations and the possible error responses.

## CORS

Browser clients are allowed by default. `CORS_ORIGINS` is `*` (any origin) or a comma
separated list such as `https://app.example.com,https://admin.example.com`. Allowed
responses carry `Access-Control-Allow-Origin`; preflight `OPTIONS` requests are answered with
the allowed methods (`GET, POST, PUT, PATCH, DELETE, OPTIONS`), headers (`Authorization,
Content-Type`) and a 600 second max age. Because authentication uses bearer tokens rather
than cookies, `*` does not expose credentials; restrict it to your frontend's origin in
production anyway.

## Route operations

Declared routes are mapped to operations by their shape. `{param}` is any path parameter.

| Route shape | Operation | Success |
| --- | --- | --- |
| `GET /<resource>` | list | 200 |
| `POST /<resource>` | create | 201 |
| `GET /<resource>/{param}` | read | 200 |
| `PUT /<resource>/{param}` | replace (all required fields) | 200 |
| `PATCH /<resource>/{param}` | update (partial) | 200 |
| `DELETE /<resource>/{param}` | delete | 204, empty body |
| `GET /<parent>/{param}/<children>` | list children of a parent, when the child references the parent | 200 |
| anything else | custom | 501 `not_implemented` until you implement it |

`<resource>` matches a model by its plural (`/posts`), singular (`/post`) or snake/kebab
name (`/blog-posts`). Every declared model also gets `GET /<resource>` if it was not
declared, matching the behaviour of earlier SEMARC versions.

## Authentication (`AUTH JWT`)

`AUTH JWT` adds:

| Route | Behaviour |
| --- | --- |
| `POST /register` | Validates the `User` fields, hashes the password, returns 201 with `user` and a token |
| `POST /login` | Exchanges `email` and `password` for a token; 401 on bad credentials |
| `GET /me` | Returns the authenticated user |
| `POST /token/refresh` | Exchanges `{"refresh_token": ...}` for a new access token and a new refresh token; the old refresh token stops working (401 if reused, expired or revoked) |
| `POST /logout` | Revokes `{"refresh_token": ...}` (204) |
| `POST /me/password` | Changes the password with `{"current_password", "new_password"}`; 422 for a wrong current password; revokes every refresh token of the user (204) |

- The account model is `User`. If the specification does not declare it, SEMARC creates it
  with `email` and `password`. If it is declared without them, they are added. `email`
  becomes unique, and `password` is a secret: it is hashed with bcrypt, never returned, and
  limited to 72 characters.
- Register, login and refresh return `access_token`, `expires_in`, `refresh_token` and
  `refresh_expires_in`. Refresh tokens are random, single use, stored only as SHA-256 hashes
  in the `refresh_tokens` table and expire after `JWT_REFRESH_TTL` seconds (default 14 days).
  Deleting a user deletes their refresh tokens.
- Tokens are HS256 JWTs signed with `JWT_SECRET` (at least 32 characters; the server refuses
  to sign with a shorter secret) and expire after `JWT_TTL` seconds (default 3600).
- Send `Authorization: Bearer <token>`. Missing, malformed, expired or orphaned tokens get 401.
- `POST /register` and `POST /login` are rate limited per client address: `AUTH_RATE_LIMIT`
  attempts (default 10) per `AUTH_RATE_WINDOW` seconds (default 60). Further attempts get
  429 `too_many_requests` with a `Retry-After` header. PHP keeps counters in
  `storage/rate-limits/`; FastAPI and NestJS keep them in memory per process. Behind a
  reverse proxy every client shares the proxy's address, so configure the proxy to forward
  the client address or adjust the limiter.

### Access policy

| Situation | Access |
| --- | --- |
| No `AUTH` declared | every route is public |
| `ROUTE ... PUBLIC` / `ROUTE ... PROTECTED` | as declared |
| Routes on the `User` model | protected |
| Other `GET` routes | public |
| Other `POST`, `PUT`, `PATCH`, `DELETE` routes | protected |

### Roles (`USE auth.roles`)

```text
USE auth.roles
ROUTE POST /sections ROLE admin editor
ROUTE DELETE /sections/{id} ROLE admin
```

- Every user has a `role` (returned by the API, never accepted from request bodies). New
  users get `user`.
- A route with `ROLE` requires a token whose user has one of the listed roles; others get
  403 `forbidden`. `ROLE` implies `PROTECTED`.
- The account that registers with the address in `BOOTSTRAP_ADMIN_EMAIL` becomes `admin`.
  Set it once to create the first administrator, then clear it.
- `PUT /users/{id}/role` with `{"role": "editor"}` changes a role (admins only). Valid
  roles are `admin`, `user` and every role named in a `ROLE` clause.
- Admins may update and delete records owned by other users.

### Ownership

When a model references `User` (for example `RELATION User HAS_MANY Post`), the record has
an owner:

- protected create requests set `user_id` from the token and ignore any `user_id` in the body;
- protected `PUT`, `PATCH` and `DELETE` requests are allowed only for the owner; anyone else
  gets 403 `forbidden` (the IR marks these operations `owner_only`);
- protected updates cannot change `user_id`;
- on public routes `user_id` is an ordinary required field and no owner check applies.

## Requests and validation

- Bodies must be JSON objects. Malformed JSON returns 400. Unknown fields are ignored.
- Types are strict: `STRING`/`TEXT` need JSON strings, `INTEGER` an integer, `FLOAT` a
  number, `BOOLEAN` `true`/`false`, `DATE` a `YYYY-MM-DD` string and `DATETIME` an ISO 8601
  string. `"5"` is not an integer. Date-times are stored in UTC and returned with a `Z` suffix.
- Fields are required unless declared `OPTIONAL`. `PATCH` accepts any subset but cannot set
  a required field to `null`.
- `VALIDATE` rules: `REQUIRED` (non-blank string), `EMAIL`, `MIN n` / `MAX n` (length for
  text, value for numbers). `STRING` columns are limited to 255 characters.
- Foreign key columns (`user_id`, `post_id`, ...) must reference an existing row, otherwise
  422. `UNIQUE` fields (and `HAS_ONE` foreign keys) return 409 when taken.

## Responses

```json
{"data": {"id": 1, "title": "Hello", "user_id": 1, "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:00:00Z"}}
```

Lists accept `?limit=` (default 20, max 100) and `?offset=`, equality filters and sorting:

- `?field=value` filters on any non-secret field, foreign key column or `id` (`DATETIME`
  fields are sortable but not filterable). Values are parsed by type: integers, numbers,
  `true`/`false` (or `1`/`0`), `YYYY-MM-DD` dates, or text. Several filters combine with AND.
- `?sort=field` sorts ascending, `?sort=-field` descending, on the same fields plus
  `created_at` and `updated_at`; ties are ordered by `id`.
- An invalid filter value or unknown sort field returns 422. Unknown query parameters are ignored.

Example: `GET /posts?user_id=3&published=true&sort=-created_at&limit=10`.


```json
{"data": [], "meta": {"total": 0, "limit": 20, "offset": 0}}
```

Records include `id`, every non-secret field, foreign key columns, `created_at` and
`updated_at` (UTC, ISO 8601).

## Errors

```json
{"error": {"code": "validation_failed", "message": "The given data was invalid.", "details": {"email": ["email must be a valid email address"]}}}
```

| Status | Code | When |
| --- | --- | --- |
| 400 | `bad_request` | Malformed JSON |
| 401 | `unauthorized` | Missing or invalid token, bad credentials |
| 403 | `forbidden` | Changing a record owned by another user |
| 404 | `not_found` | Unknown route or record |
| 409 | `conflict` | Unique value taken, or deleting a record that others still reference |
| 429 | `too_many_requests` | Too many `/register` or `/login` attempts; see `Retry-After` |
| 422 | `validation_failed` | Input rules failed; `details` lists messages per field |
| 501 | `not_implemented` | A declared custom route that has no generated behaviour |
| 500 | `internal_error` | Unexpected error (details are logged, not returned) |

The exact wording of validation messages follows each framework; the codes, statuses and
`details` keys are the same everywhere.

## Deletes

Deleting a record that other rows reference returns 409 instead of cascading. Delete the
children first, or change the generated service if you want different behaviour.

## Verification

`api_scenario.json` (in `tests/` for PHP and FastAPI, `test/` for NestJS) is generated by
`semarc/generator/utils/api_scenario.py`. It is an ordered list of steps: register, login, create,
read, list, update, replace, nested listing, custom routes and deletes, plus the negative
cases (401 without a token, 403 when a second user changes someone else's record, 404 for
missing records, 409 for duplicates and protected deletes, 422 for invalid input, 429 once
the login limit is exceeded).

- `php tests/run.php`, `pytest` or `npm test` replays it in-process on SQLite.
- `python3 scripts/e2e_runtime.py` replays it over HTTP against `docker compose` stacks for
  MySQL, PostgreSQL and SQLite.

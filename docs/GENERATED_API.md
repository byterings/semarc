# Generated API Contract

Every target (PHP, FastAPI, NestJS) generates an API with the same observable behaviour.
The behaviour is decided in the architecture layer (`architecture/resource_planner.py`)
and expressed in the Architecture IR; generators only translate it.

The contract is verified by `api_scenario.json`, which SEMARC writes into every generated
project (see [Verification](#verification)).

## Built-in endpoints

| Method | Path | Response |
| --- | --- | --- |
| GET | `/` | HTML overview of the project, models and routes |
| GET | `/health` | `{"status": "ok", "project": "...", "database": "ok"}`, or 503 with `database: "unavailable"` |
| GET | `/routes` | `{"routes": ["GET /", ...]}` |

These paths are reserved and cannot be declared with `ROUTE`.

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

- The account model is `User`. If the specification does not declare it, SEMARC creates it
  with `email` and `password`. If it is declared without them, they are added. `email`
  becomes unique, and `password` is a secret: it is hashed with bcrypt, never returned, and
  limited to 72 characters.
- Tokens are HS256 JWTs signed with `JWT_SECRET` (at least 32 characters; the server refuses
  to sign with a shorter secret) and expire after `JWT_TTL` seconds (default 3600).
- Send `Authorization: Bearer <token>`. Missing, malformed, expired or orphaned tokens get 401.

### Access policy

| Situation | Access |
| --- | --- |
| No `AUTH` declared | every route is public |
| `ROUTE ... PUBLIC` / `ROUTE ... PROTECTED` | as declared |
| Routes on the `User` model | protected |
| Other `GET` routes | public |
| Other `POST`, `PUT`, `PATCH`, `DELETE` routes | protected |

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
  number, `BOOLEAN` `true`/`false`. `"5"` is not an integer.
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

Lists accept `?limit=` (default 20, max 100) and `?offset=`:

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
`generator/utils/api_scenario.py`. It is an ordered list of steps: register, login, create,
read, list, update, replace, nested listing, custom routes and deletes, plus the negative
cases (401 without a token, 403 when a second user changes someone else's record, 404 for
missing records, 409 for duplicates and protected deletes, 422 for invalid input).

- `php tests/run.php`, `pytest` or `npm test` replays it in-process on SQLite.
- `python3 scripts/e2e_runtime.py` replays it over HTTP against `docker compose` stacks for
  MySQL, PostgreSQL and SQLite.

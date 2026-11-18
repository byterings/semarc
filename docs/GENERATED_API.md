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
- `POST /register`, `POST /login` and the other credential endpoints are rate limited per
  client address: `AUTH_RATE_LIMIT` attempts (default 10) per `AUTH_RATE_WINDOW` seconds
  (default 60). Further attempts get 429 `too_many_requests` with a `Retry-After` header.
- Counters are local by default: PHP keeps them in `storage/rate-limits/`, FastAPI and
  NestJS in memory per process. With `USE cache.redis` they are kept in Redis
  (`RATE_LIMIT_STORE=redis`, `REDIS_URL`, `redis://` or `rediss://`), so every process and
  server shares them; the generated `docker-compose.yml` then runs Redis. If Redis cannot be
  reached the limiter logs the error and counts locally instead of failing requests.
- Behind a reverse proxy or load balancer set `TRUSTED_PROXIES` to its addresses or CIDR
  ranges (comma separated). `X-Forwarded-For` is used only when the direct peer is trusted;
  the client is then the rightmost forwarded address that is not a trusted proxy. Without
  it, forwarded headers are ignored, so a client cannot dodge the limit by forging them.

### Cookie sessions (`AUTH SESSION`)

`AUTH SESSION` has the same routes, rules and modules as `AUTH JWT`, with these differences:

- Register, login and OAuth sign-in start a session: the response sets an HttpOnly,
  `SameSite=Lax` cookie `session` (and `Secure` when `APP_ENV=production` or
  `SESSION_SECURE_COOKIE=true`) and a readable cookie `csrf_token`, and returns
  `csrf_token` and `expires_in` instead of tokens.
- Requests authenticate with the cookie. `POST`, `PUT`, `PATCH` and `DELETE` requests on a
  session must also send the `csrf_token` value in the `X-CSRF-Token` header; without it they
  get 403 `forbidden`. The front end can read the value from the `csrf_token` cookie after a
  page reload.
- Sessions are stored as SHA-256 hashes in the `sessions` table and expire after
  `SESSION_TTL` seconds (default 14 days). `POST /logout` (authenticated) ends the current
  session and clears both cookies. Changing or resetting the password ends every session of
  the user. There is no `POST /token/refresh`.
- Browsers send cookies cross-origin only to origins listed in `CORS_ORIGINS`; then the
  API answers with `Access-Control-Allow-Credentials: true`. With `CORS_ORIGINS=*` cookie
  sessions work for same-origin front ends only (for example behind one reverse proxy).
- `JWT_SECRET` is still used to sign OAuth `state`.

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

### Password reset and email verification

```text
USE auth.password_reset
USE auth.email_verification
```

| Route | Behaviour |
| --- | --- |
| `POST /password/forgot` | `{"email": ...}`; emails a reset token when the account exists. Always 202, so the response does not reveal which addresses have accounts. Rate limited like login |
| `POST /password/reset` | `{"token", "password"}`; sets the new password (same rules as registration), revokes every refresh token of the user (204); 422 for an unknown, used or expired token |
| `POST /email/verify` | `{"token": ...}`; marks the address verified and returns the user (200); 422 for an unknown, used or expired token |
| `POST /email/resend` | Protected; emails a new verification token when the address is not verified yet (202) |

- Tokens are 64 random hexadecimal characters, single use and stored only as SHA-256
  hashes (`password_resets`, `email_verifications`). Reset tokens expire after one hour,
  verification tokens after 24 hours. Deleting a user deletes their tokens.
- With `auth.email_verification`, `User` gets a managed `email_verified_at` field (`null`
  until verified, never accepted from request bodies) and registration sends the
  verification email. Unverified users can still log in; check `email_verified_at` where
  your business rules need a verified address.
- Emails are plain text and contain the token. When `APP_URL` is set they also contain a
  link to `<APP_URL>/reset-password?token=...` or `<APP_URL>/verify-email?token=...` for
  your front end.

Mail settings:

| Variable | Default | Meaning |
| --- | --- | --- |
| `MAIL_DRIVER` | `log` | `smtp` sends mail; `log` writes it to the application log; `memory` keeps it in process (tests) |
| `MAIL_HOST`, `MAIL_PORT` | | SMTP server |
| `MAIL_USERNAME`, `MAIL_PASSWORD` | | SMTP credentials (optional) |
| `MAIL_ENCRYPTION` | `none` | `tls` for STARTTLS, `ssl` for implicit TLS |
| `MAIL_FROM` | `no-reply@<project>.local` | Sender address |
| `APP_URL` | | Front-end base URL used for links in emails |

The generated `docker-compose.yml` runs [Mailpit](https://mailpit.axllent.org/) as a local
SMTP server (`MAIL_DRIVER=smtp`): every email sent by the API appears at
http://localhost:8025 (`MAIL_UI_PORT` changes the port). Point `MAIL_*` at a real provider before deploying.

### Sign in with Google and GitHub (`USE auth.oauth.google`, `USE auth.oauth.github`)

| Route | Behaviour |
| --- | --- |
| `GET /oauth/<provider>` | Returns `authorization_url` and `state` (200); 503 when the provider is not configured |
| `POST /oauth/<provider>/callback` | `{"code", "state"}`; signs the user in and returns `user` and tokens like `POST /register` (200). Rate limited like login |

The flow, for a front end at `https://app.example.com`:

1. The front end calls `GET /oauth/google`, stores `state` (for example in `sessionStorage`)
   and redirects the browser to `authorization_url`.
2. The provider redirects to `OAUTH_GOOGLE_REDIRECT_URI` (a front-end page) with `code` and
   `state` in the query string. The front end checks that `state` equals the stored value.
3. The front end posts both to `POST /oauth/google/callback` and receives the session.

The API exchanges the code with the client secret, so the secret never reaches the browser.

- `state` is signed with `JWT_SECRET`, bound to the provider and valid for 10 minutes.
  Unknown, expired or tampered states get 422. Invalid or expired codes get 422; an
  unreachable provider gets 502 `bad_gateway`.
- Only an email address the provider marks as verified is accepted (Google:
  `email_verified`; GitHub: the primary address from `/user/emails`); otherwise 422.
- The identity is stored in `oauth_accounts` (`provider_subject` such as `google:1234`). On
  the next sign-in the same user is found even if the email changed at the provider.
- Without a linked identity, the user with the same email is linked. If that account has not
  verified its address (always, without `auth.email_verification`), its password is replaced
  by a random one and its refresh tokens are revoked: whoever registered the address first
  cannot keep access to an account the address owner now uses. The owner can set a password
  again through password reset.
- Otherwise a user is created with a random password, `name` from the provider profile (or
  the part of the email before `@`), the default role (`admin` for `BOOTSTRAP_ADMIN_EMAIL`)
  and, with `auth.email_verification`, a verified address.
- Because users are created from a profile, every other `User` field must be `OPTIONAL`, and
  `User` cannot reference another model. The validator enforces both.

| Variable | Meaning |
| --- | --- |
| `OAUTH_GOOGLE_CLIENT_ID`, `OAUTH_GOOGLE_CLIENT_SECRET` | OAuth client from Google Cloud Console (Credentials → OAuth client ID, type Web application) |
| `OAUTH_GOOGLE_REDIRECT_URI` | Front-end page that receives the redirect; register it as an authorized redirect URI |
| `OAUTH_GITHUB_CLIENT_ID`, `OAUTH_GITHUB_CLIENT_SECRET` | OAuth app from GitHub → Settings → Developer settings → OAuth Apps |
| `OAUTH_GITHUB_REDIRECT_URI` | Must match the app's authorization callback URL |
| `OAUTH_<PROVIDER>_ENDPOINT` | Testing only: replaces the provider origin, for example with `scripts/oauth_mock.py` |

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

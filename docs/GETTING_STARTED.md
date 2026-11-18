# Getting Started

From nothing to a running, documented API in about five minutes.

## 1. Install

You need Python 3.11+ for SEMARC and Docker to run the generated project.

```bash
pipx install semarc      # or: pip install semarc
semarc version
```

## 2. Write a specification

Start from a starter instead of a blank file:

```bash
semarc init bookshop --starter shop --target fastapi --database postgresql
```

This writes `bookshop.sem`. Open it: every line is a declaration.

```text
PROJECT Bookshop
TARGET FASTAPI
DATABASE POSTGRESQL
AUTH JWT

MODEL Product
    name STRING
    sku STRING UNIQUE
    price_cents INTEGER
    active BOOLEAN OPTIONAL

RELATION User HAS_MANY Order
RELATION Product HAS_MANY Order

VALIDATE price_cents MIN 0

ROUTE GET /products
ROUTE POST /products
ROUTE GET /orders PROTECTED
```

- `MODEL` blocks declare tables and fields (`STRING`, `TEXT`, `INTEGER`, `FLOAT`, `BOOLEAN`,
  `DATE`, `DATETIME`), with `UNIQUE` and `OPTIONAL` modifiers.
- `RELATION` adds foreign keys; `User HAS_MANY Order` also makes each order owned by a user.
- `VALIDATE` adds input rules (`REQUIRED`, `EMAIL`, `MIN n`, `MAX n`).
- `ROUTE` declares endpoints. The shape decides the behaviour: `GET /products` lists,
  `GET /products/{id}` reads, `PATCH /products/{id}` updates, and so on.
- `AUTH JWT` issues bearer tokens; `AUTH SESSION` uses cookie sessions for browser front ends.
- With `AUTH JWT`, reads are public and writes need a token; add `PUBLIC` or `PROTECTED` to a
  route to change that.

The full language is in [SEMANTIC_LANGUAGE_SPEC.md](SEMANTIC_LANGUAGE_SPEC.md).

## 3. Check it

```bash
semarc check bookshop.sem
```

`check` validates the file and prints every endpoint with its access rule, plus architecture
diagnostics. Nothing is written. Errors point at the line to fix.

## 4. Generate and run

```bash
semarc build bookshop.sem --output bookshop
cd bookshop
docker compose up --build
```

Open http://localhost:8000/docs for interactive documentation (NestJS projects use port 3000).
If the port is taken, run `APP_PORT=8080 docker compose up --build`.

## 5. Try the API

```bash
curl -X POST localhost:8000/register -H 'Content-Type: application/json' \
  -d '{"name": "Ada", "email": "ada@example.com", "password": "correct-horse"}'
# copy data.access_token from the response
curl -X POST localhost:8000/products -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name": "SEMARC in Action", "sku": "BOOK-1", "price_cents": 2900}'
curl 'localhost:8000/products?sort=-price_cents'
```

## 6. Run the generated tests

Every project ships `api_scenario.json`, the behaviour SEMARC derived from your
specification, and a runner for it:

| Target | Command |
| --- | --- |
| PHP | `php tests/run.php` |
| FastAPI | `pip install -r requirements.txt && pytest` |
| NestJS | `npm install && npm test` |

## 7. Make it yours

The generated project is ordinary code: change it, add business logic, deploy it. Before you
deploy, set a real `JWT_SECRET` (32+ characters), restrict `CORS_ORIGINS`, and read
[GENERATED_API.md](GENERATED_API.md) for the full behaviour, including rate limits and
ownership rules.

To change the architecture later, edit the `.sem` file and generate again into a new
directory, then compare.

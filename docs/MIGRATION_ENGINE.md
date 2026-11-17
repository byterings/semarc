# Migration Engine

Migrations are planned once, target-neutrally, and rendered by each target in its own
migration format.

## Planning

1. `RelationshipEngine` derives one foreign key per relationship (de-duplicated when both
   directions are declared; unique for `HAS_ONE`).
2. `ResourcePlanner` produces the final model specs, including fields added by `AUTH JWT`
   and the auth-created `User` model.
3. `ArchitectureIRBuilder` writes `ir["migrations"]["tables"]`: one table per model with its
   fields (`type`, `required`, `unique`) and foreign keys.
4. `ArchitectureOptimizer` orders the tables topologically so that referenced tables are
   created first (ties broken by name) and assigns `sequence`.

Every table also gets `id` (auto-increment primary key), `created_at` and `updated_at`.

## Type Mapping

| Semantic | MySQL | PostgreSQL | SQLite |
| --- | --- | --- | --- |
| `STRING` | VARCHAR(255) | VARCHAR(255) | VARCHAR(255) |
| `TEXT` | TEXT | TEXT | TEXT |
| `INTEGER` | INT | INTEGER | INTEGER |
| `FLOAT` | DOUBLE | DOUBLE PRECISION | REAL |
| `BOOLEAN` | TINYINT(1) | BOOLEAN | INTEGER/BOOLEAN |
| timestamps | DATETIME | TIMESTAMP | TEXT/DATETIME |

Foreign keys are `INTEGER NOT NULL` with a constraint to the parent's `id` and an index
(or a unique constraint for `HAS_ONE`). Deletes are restricted; the generated services
answer 409 before the database would refuse.

## Target Formats

| Target | Files | Applied by |
| --- | --- | --- |
| PHP | `migrations/NNN_create_<table>_table.php` returning a table definition; `core/Schema.php` builds driver-specific DDL | `php bin/migrate.php` (tracks `schema_migrations`) |
| FastAPI | `migrations/versions/NNNN_create_<table>_table.py` Alembic revisions chained by sequence | `python migrate.py` (`alembic upgrade head`) |
| NestJS | `src/database/migrations/<timestamp>-create-<table>-table.ts` using TypeORM `Table` | automatically on start (`migrationsRun`), or `npm run migration:run` |

All three are database-neutral: the same files work on MySQL, PostgreSQL and SQLite.

## Boundary

The migration plan contains no SQL or framework syntax. Targets render it only.

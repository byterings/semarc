<?php

declare(strict_types=1);

/**
 * Generic PDO persistence for one table. Model repositories extend this class
 * and are the place to add custom queries.
 */
abstract class Repository
{
    protected PDO $connection;

    public function __construct(protected readonly string $table)
    {
        $this->connection = Database::connection();
    }

    /**
     * @param array<string, mixed> $where
     * @return list<array<string, mixed>>
     */
    public function paginate(int $limit, int $offset, array $where = []): array
    {
        [$clause, $bindings] = $this->where($where);
        $statement = $this->connection->prepare(
            'SELECT * FROM ' . Database::quote($this->table) . $clause
            . ' ORDER BY ' . Database::quote('id') . ' LIMIT ' . $limit . ' OFFSET ' . $offset
        );
        $this->execute($statement, $bindings);

        return $statement->fetchAll();
    }

    /**
     * @param array<string, mixed> $where
     */
    public function count(array $where = []): int
    {
        [$clause, $bindings] = $this->where($where);
        $statement = $this->connection->prepare('SELECT COUNT(*) FROM ' . Database::quote($this->table) . $clause);
        $this->execute($statement, $bindings);

        return (int) $statement->fetchColumn();
    }

    /**
     * @return array<string, mixed>|null
     */
    public function findById(int $id): ?array
    {
        return $this->findBy('id', $id);
    }

    /**
     * @return array<string, mixed>|null
     */
    public function findBy(string $column, mixed $value): ?array
    {
        $statement = $this->connection->prepare(
            'SELECT * FROM ' . Database::quote($this->table) . ' WHERE ' . Database::quote($column) . ' = ? LIMIT 1'
        );
        $this->execute($statement, [$value]);
        $row = $statement->fetch();

        return $row === false ? null : $row;
    }

    public function existsWhere(string $column, mixed $value, ?int $exceptId = null): bool
    {
        $sql = 'SELECT 1 FROM ' . Database::quote($this->table) . ' WHERE ' . Database::quote($column) . ' = ?';
        $bindings = [$value];
        if ($exceptId !== null) {
            $sql .= ' AND ' . Database::quote('id') . ' <> ?';
            $bindings[] = $exceptId;
        }
        $statement = $this->connection->prepare($sql . ' LIMIT 1');
        $this->execute($statement, $bindings);

        return $statement->fetchColumn() !== false;
    }

    public function rowExists(string $table, int $id): bool
    {
        $statement = $this->connection->prepare(
            'SELECT 1 FROM ' . Database::quote($table) . ' WHERE ' . Database::quote('id') . ' = ? LIMIT 1'
        );
        $this->execute($statement, [$id]);

        return $statement->fetchColumn() !== false;
    }

    public function countIn(string $table, string $column, int $id): int
    {
        $statement = $this->connection->prepare(
            'SELECT COUNT(*) FROM ' . Database::quote($table) . ' WHERE ' . Database::quote($column) . ' = ?'
        );
        $this->execute($statement, [$id]);

        return (int) $statement->fetchColumn();
    }

    /**
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    public function create(array $data): array
    {
        $now = Database::now();
        $data += ['created_at' => $now, 'updated_at' => $now];
        $columns = array_keys($data);
        $sql = 'INSERT INTO ' . Database::quote($this->table)
            . ' (' . implode(', ', array_map([Database::class, 'quote'], $columns)) . ')'
            . ' VALUES (' . implode(', ', array_fill(0, count($columns), '?')) . ')';

        if (Database::driver() === 'pgsql') {
            $statement = $this->connection->prepare($sql . ' RETURNING ' . Database::quote('id'));
            $this->execute($statement, array_values($data));
            $id = (int) $statement->fetchColumn();
        } else {
            $statement = $this->connection->prepare($sql);
            $this->execute($statement, array_values($data));
            $id = (int) $this->connection->lastInsertId();
        }

        return $this->findById($id) ?? throw new RuntimeException("Created row {$id} could not be loaded.");
    }

    /**
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    public function update(int $id, array $data): array
    {
        $data['updated_at'] = Database::now();
        $assignments = array_map(fn (string $column): string => Database::quote($column) . ' = ?', array_keys($data));
        $statement = $this->connection->prepare(
            'UPDATE ' . Database::quote($this->table) . ' SET ' . implode(', ', $assignments)
            . ' WHERE ' . Database::quote('id') . ' = ?'
        );
        $this->execute($statement, [...array_values($data), $id]);

        return $this->findById($id) ?? throw new RuntimeException("Updated row {$id} could not be loaded.");
    }

    public function delete(int $id): void
    {
        $statement = $this->connection->prepare(
            'DELETE FROM ' . Database::quote($this->table) . ' WHERE ' . Database::quote('id') . ' = ?'
        );
        $this->execute($statement, [$id]);
    }

    /**
     * @param array<string, mixed> $where
     * @return array{0: string, 1: list<mixed>}
     */
    private function where(array $where): array
    {
        if ($where === []) {
            return ['', []];
        }
        $conditions = array_map(fn (string $column): string => Database::quote($column) . ' = ?', array_keys($where));

        return [' WHERE ' . implode(' AND ', $conditions), array_values($where)];
    }

    /**
     * @param list<mixed> $bindings
     */
    private function execute(PDOStatement $statement, array $bindings): void
    {
        foreach (array_values($bindings) as $index => $value) {
            $type = match (true) {
                is_bool($value) => PDO::PARAM_BOOL,
                is_int($value) => PDO::PARAM_INT,
                $value === null => PDO::PARAM_NULL,
                default => PDO::PARAM_STR,
            };
            $statement->bindValue($index + 1, $value, $type);
        }
        $statement->execute();
    }
}

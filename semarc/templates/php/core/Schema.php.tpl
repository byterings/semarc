<?php

declare(strict_types=1);

/**
 * Builds driver-specific DDL from the table definitions in migrations/.
 */
final class Schema
{
    private const TYPES = [
        'mysql' => ['STRING' => 'VARCHAR(255)', 'TEXT' => 'TEXT', 'INTEGER' => 'INT', 'FLOAT' => 'DOUBLE', 'DECIMAL' => 'DECIMAL(12,2)', 'BOOLEAN' => 'TINYINT(1)', 'DATE' => 'DATE', 'DATETIME' => 'DATETIME'],
        'pgsql' => ['STRING' => 'VARCHAR(255)', 'TEXT' => 'TEXT', 'INTEGER' => 'INTEGER', 'FLOAT' => 'DOUBLE PRECISION', 'DECIMAL' => 'NUMERIC(12,2)', 'BOOLEAN' => 'BOOLEAN', 'DATE' => 'DATE', 'DATETIME' => 'TIMESTAMP'],
        'sqlite' => ['STRING' => 'VARCHAR(255)', 'TEXT' => 'TEXT', 'INTEGER' => 'INTEGER', 'FLOAT' => 'REAL', 'DECIMAL' => 'NUMERIC', 'BOOLEAN' => 'INTEGER', 'DATE' => 'TEXT', 'DATETIME' => 'TEXT'],
    ];

    private const PRIMARY_KEYS = [
        'mysql' => 'INT AUTO_INCREMENT PRIMARY KEY',
        'pgsql' => 'SERIAL PRIMARY KEY',
        'sqlite' => 'INTEGER PRIMARY KEY AUTOINCREMENT',
    ];

    /**
     * @param array{table: string, columns: list<array>, foreign_keys: list<array>} $definition
     * @return list<string>
     */
    public static function createTable(array $definition, string $driver): array
    {
        $quote = static fn (string $name): string => $driver === 'mysql' ? '`' . $name . '`' : '"' . $name . '"';
        $types = self::TYPES[$driver] ?? throw new RuntimeException("Unsupported driver: {$driver}");

        $lines = [$quote('id') . ' ' . self::PRIMARY_KEYS[$driver]];
        foreach ($definition['columns'] as $column) {
            $lines[] = $quote($column['name']) . ' ' . $types[$column['type']] . ($column['required'] ? ' NOT NULL' : ' NULL');
        }
        foreach ($definition['foreign_keys'] as $foreignKey) {
            $lines[] = $quote($foreignKey['column']) . ' ' . $types['INTEGER'] . ' NOT NULL';
        }
        $lines[] = $quote('created_at') . ' ' . $types['DATETIME'] . ' NOT NULL';
        $lines[] = $quote('updated_at') . ' ' . $types['DATETIME'] . ' NOT NULL';

        foreach ($definition['columns'] as $column) {
            if ($column['unique']) {
                $lines[] = 'UNIQUE (' . $quote($column['name']) . ')';
            }
        }
        foreach ($definition['foreign_keys'] as $foreignKey) {
            if ($foreignKey['unique']) {
                $lines[] = 'UNIQUE (' . $quote($foreignKey['column']) . ')';
            }
            $onDelete = ($foreignKey['on_delete'] ?? 'RESTRICT') === 'CASCADE' ? ' ON DELETE CASCADE' : '';
            $lines[] = 'FOREIGN KEY (' . $quote($foreignKey['column']) . ') REFERENCES '
                . $quote($foreignKey['references']) . ' (' . $quote('id') . ')' . $onDelete;
        }

        $suffix = $driver === 'mysql' ? ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4' : '';
        $statements = [
            'CREATE TABLE ' . $quote($definition['table']) . " (\n    " . implode(",\n    ", $lines) . "\n)" . $suffix,
        ];

        foreach ($definition['columns'] as $column) {
            if (!empty($column['index'])) {
                $index = 'idx_' . $definition['table'] . '_' . $column['name'];
                $statements[] = 'CREATE INDEX ' . $quote($index) . ' ON ' . $quote($definition['table']) . ' (' . $quote($column['name']) . ')';
            }
        }
        if ($driver !== 'mysql') {
            foreach ($definition['foreign_keys'] as $foreignKey) {
                if (!$foreignKey['unique']) {
                    $index = 'idx_' . $definition['table'] . '_' . $foreignKey['column'];
                    $statements[] = 'CREATE INDEX ' . $quote($index) . ' ON ' . $quote($definition['table']) . ' (' . $quote($foreignKey['column']) . ')';
                }
            }
        }

        return $statements;
    }
}

<?php

declare(strict_types=1);

final class Migrator
{
    public function __construct(
        private readonly PDO $connection,
        private readonly string $directory,
    ) {
    }

    /**
     * Applies pending migrations in filename order.
     *
     * @return list<string> applied migration names
     */
    public function run(): array
    {
        $driver = (string) $this->connection->getAttribute(PDO::ATTR_DRIVER_NAME);
        $quote = static fn (string $name): string => $driver === 'mysql' ? '`' . $name . '`' : '"' . $name . '"';

        $this->connection->exec(
            'CREATE TABLE IF NOT EXISTS ' . $quote('schema_migrations')
            . ' (' . $quote('migration') . ' VARCHAR(255) PRIMARY KEY, ' . $quote('applied_at') . ' VARCHAR(32) NOT NULL)'
        );
        $applied = $this->connection
            ->query('SELECT ' . $quote('migration') . ' FROM ' . $quote('schema_migrations'))
            ->fetchAll(PDO::FETCH_COLUMN);

        $files = glob($this->directory . '/*.php') ?: [];
        sort($files);

        $ran = [];
        foreach ($files as $file) {
            $name = basename($file, '.php');
            if (in_array($name, $applied, true)) {
                continue;
            }

            $definition = require $file;
            foreach (Schema::createTable($definition, $driver) as $statement) {
                $this->connection->exec($statement);
            }

            $insert = $this->connection->prepare(
                'INSERT INTO ' . $quote('schema_migrations') . ' (' . $quote('migration') . ', ' . $quote('applied_at') . ') VALUES (?, ?)'
            );
            $insert->execute([$name, gmdate('Y-m-d H:i:s')]);
            $ran[] = $name;
        }

        return $ran;
    }
}

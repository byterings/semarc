<?php

declare(strict_types=1);

final class Database
{
    private static ?PDO $connection = null;

    public static function connection(): PDO
    {
        if (self::$connection === null) {
            self::$connection = self::connect(require __DIR__ . '/../config/database.php');
        }

        return self::$connection;
    }

    public static function setConnection(?PDO $connection): void
    {
        self::$connection = $connection;
    }

    public static function driver(): string
    {
        return (string) self::connection()->getAttribute(PDO::ATTR_DRIVER_NAME);
    }

    public static function quote(string $identifier): string
    {
        return self::driver() === 'mysql' ? '`' . $identifier . '`' : '"' . $identifier . '"';
    }

    public static function now(): string
    {
        return gmdate('Y-m-d H:i:s');
    }

    /**
     * @param array<string, string> $config
     */
    private static function connect(array $config): PDO
    {
        $options = [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ];

        switch ($config['driver']) {
            case 'sqlite':
                $path = $config['database'];
                if ($path !== ':memory:' && !is_dir(dirname($path))) {
                    mkdir(dirname($path), 0775, true);
                }
                $connection = new PDO('sqlite:' . $path, null, null, $options);
                $connection->exec('PRAGMA foreign_keys = ON');

                return $connection;
            case 'mysql':
                $dsn = sprintf('mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4', $config['host'], $config['port'], $config['database']);

                return new PDO($dsn, $config['username'], $config['password'], $options);
            case 'pgsql':
                $dsn = sprintf('pgsql:host=%s;port=%s;dbname=%s', $config['host'], $config['port'], $config['database']);

                return new PDO($dsn, $config['username'], $config['password'], $options);
        }

        throw new RuntimeException('Unsupported DB_CONNECTION: ' . $config['driver'] . ' (use mysql, pgsql or sqlite).');
    }
}

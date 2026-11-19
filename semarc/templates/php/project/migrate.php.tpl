<?php

declare(strict_types=1);

require_once __DIR__ . '/../bootstrap.php';

// Waits for the database (useful while Docker starts it), then applies pending migrations.
$attempts = (int) (Env::get('DB_CONNECT_ATTEMPTS', '30'));
for ($attempt = 1; ; $attempt++) {
    try {
        $connection = Database::connection();
        break;
    } catch (PDOException $exception) {
        if ($attempt >= $attempts) {
            fwrite(STDERR, 'Database connection failed: ' . $exception->getMessage() . PHP_EOL);
            exit(1);
        }
        fwrite(STDERR, "Waiting for database ({$attempt}/{$attempts})..." . PHP_EOL);
        sleep(1);
    }
}

$applied = (new Migrator($connection, __DIR__ . '/../migrations'))->run();
echo $applied === [] ? 'Nothing to migrate.' . PHP_EOL : 'Applied:' . PHP_EOL . '- ' . implode(PHP_EOL . '- ', $applied) . PHP_EOL;

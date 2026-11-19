<?php

declare(strict_types=1);

/**
 * Single-use, expiring tokens (password reset, email verification). Only a SHA-256 hash
 * of each token is stored.
 */
final class OneTimeTokens
{
    public function __construct(private readonly string $table)
    {
    }

    public function issue(int $userId, int $ttlSeconds): string
    {
        $token = bin2hex(random_bytes(32));
        $now = Database::now();
        $statement = Database::connection()->prepare(
            'INSERT INTO ' . Database::quote($this->table) . ' ('
            . implode(', ', array_map([Database::class, 'quote'], ['user_id', 'token_hash', 'expires_at', 'created_at', 'updated_at']))
            . ') VALUES (?, ?, ?, ?, ?)'
        );
        $statement->execute([$userId, hash('sha256', $token), gmdate('Y-m-d H:i:s', time() + $ttlSeconds), $now, $now]);

        return $token;
    }

    /** Marks a valid token as used and returns its user id, or null when invalid, used or expired. */
    public function consume(string $token): ?int
    {
        $statement = Database::connection()->prepare(
            'SELECT * FROM ' . Database::quote($this->table) . ' WHERE ' . Database::quote('token_hash') . ' = ? LIMIT 1'
        );
        $statement->execute([hash('sha256', $token)]);
        $row = $statement->fetch();
        if ($row === false || $row['used_at'] !== null || strtotime((string) $row['expires_at'] . ' UTC') <= time()) {
            return null;
        }

        $update = Database::connection()->prepare(
            'UPDATE ' . Database::quote($this->table) . ' SET ' . Database::quote('used_at') . ' = ?, '
            . Database::quote('updated_at') . ' = ? WHERE ' . Database::quote('id') . ' = ? AND '
            . Database::quote('used_at') . ' IS NULL'
        );
        $update->execute([Database::now(), Database::now(), $row['id']]);

        return $update->rowCount() === 1 ? (int) $row['user_id'] : null;
    }
}

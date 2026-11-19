<?php

declare(strict_types=1);

/**
 * Opaque, rotating refresh tokens. Only a SHA-256 hash of each token is stored.
 */
final class RefreshTokens
{
    private const TABLE = '{{table}}';

    public static function ttl(): int
    {
        return (int) Env::get('JWT_REFRESH_TTL', '{{ttl}}');
    }

    /**
     * @return array{refresh_token: string, refresh_expires_in: int}
     */
    public function issue(int $userId): array
    {
        $token = bin2hex(random_bytes(32));
        $now = Database::now();
        $statement = Database::connection()->prepare(
            'INSERT INTO ' . Database::quote(self::TABLE) . ' ('
            . implode(', ', array_map([Database::class, 'quote'], ['user_id', 'token_hash', 'expires_at', 'created_at', 'updated_at']))
            . ') VALUES (?, ?, ?, ?, ?)'
        );
        $statement->execute([$userId, hash('sha256', $token), gmdate('Y-m-d H:i:s', time() + self::ttl()), $now, $now]);

        return ['refresh_token' => $token, 'refresh_expires_in' => self::ttl()];
    }

    /** Revokes a valid token and returns its user id; invalid, expired or reused tokens get 401. */
    public function rotate(string $token): int
    {
        $statement = Database::connection()->prepare(
            'SELECT * FROM ' . Database::quote(self::TABLE) . ' WHERE ' . Database::quote('token_hash') . ' = ? LIMIT 1'
        );
        $statement->execute([hash('sha256', $token)]);
        $row = $statement->fetch();
        if ($row === false || $row['revoked_at'] !== null || strtotime((string) $row['expires_at'] . ' UTC') <= time()) {
            throw HttpException::unauthorized('Invalid or expired refresh token.');
        }
        $this->revoke($token);

        return (int) $row['user_id'];
    }

    public function revoke(string $token): void
    {
        $statement = Database::connection()->prepare(
            'UPDATE ' . Database::quote(self::TABLE) . ' SET ' . Database::quote('revoked_at') . ' = ?, '
            . Database::quote('updated_at') . ' = ? WHERE ' . Database::quote('token_hash') . ' = ? AND '
            . Database::quote('revoked_at') . ' IS NULL'
        );
        $statement->execute([Database::now(), Database::now(), hash('sha256', $token)]);
    }

    public function revokeAll(int $userId): void
    {
        $statement = Database::connection()->prepare(
            'UPDATE ' . Database::quote(self::TABLE) . ' SET ' . Database::quote('revoked_at') . ' = ?, '
            . Database::quote('updated_at') . ' = ? WHERE ' . Database::quote('user_id') . ' = ? AND '
            . Database::quote('revoked_at') . ' IS NULL'
        );
        $statement->execute([Database::now(), Database::now(), $userId]);
    }
}

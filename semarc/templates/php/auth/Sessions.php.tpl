<?php

declare(strict_types=1);

/**
 * Server-side sessions behind an HttpOnly cookie. Only SHA-256 hashes of the session token
 * and of its CSRF token are stored. POST, PUT, PATCH and DELETE requests must send the CSRF
 * token (also readable from the {{csrf_cookie}} cookie) in the {{csrf_header}} header.
 */
final class Sessions
{
    private const TABLE = '{{table}}';
    public const COOKIE = '{{cookie}}';
    public const CSRF_COOKIE = '{{csrf_cookie}}';
    public const CSRF_HEADER = '{{csrf_header_lower}}';

    public static function ttl(): int
    {
        return (int) Env::get('SESSION_TTL', '{{ttl}}');
    }

    /**
     * Starts a session: stores it and queues the session and CSRF cookies.
     *
     * @return array{csrf_token: string, expires_in: int}
     */
    public function issue(int $userId): array
    {
        $token = bin2hex(random_bytes(32));
        $csrf = bin2hex(random_bytes(32));
        $now = Database::now();
        $statement = Database::connection()->prepare(
            'INSERT INTO ' . Database::quote(self::TABLE) . ' ('
            . implode(', ', array_map([Database::class, 'quote'], ['user_id', 'token_hash', 'csrf_hash', 'expires_at', 'created_at', 'updated_at']))
            . ') VALUES (?, ?, ?, ?, ?, ?)'
        );
        $statement->execute([$userId, hash('sha256', $token), hash('sha256', $csrf), gmdate('Y-m-d H:i:s', time() + self::ttl()), $now, $now]);
        Cookies::queue(self::COOKIE, $token, self::ttl(), true);
        Cookies::queue(self::CSRF_COOKIE, $csrf, self::ttl(), false);

        return ['csrf_token' => $csrf, 'expires_in' => self::ttl()];
    }

    /**
     * The active session for the request cookie, or null when missing, ended or expired.
     *
     * @return array<string, mixed>|null
     */
    public function find(Request $request): ?array
    {
        $token = $request->cookie(self::COOKIE);
        if ($token === null || $token === '') {
            return null;
        }
        $statement = Database::connection()->prepare(
            'SELECT * FROM ' . Database::quote(self::TABLE) . ' WHERE ' . Database::quote('token_hash') . ' = ? LIMIT 1'
        );
        $statement->execute([hash('sha256', $token)]);
        $row = $statement->fetch();
        if ($row === false || $row['revoked_at'] !== null || strtotime((string) $row['expires_at'] . ' UTC') <= time()) {
            return null;
        }

        return $row;
    }

    /** Ends the request's session and clears its cookies. */
    public function end(Request $request): void
    {
        $token = (string) $request->cookie(self::COOKIE);
        $statement = Database::connection()->prepare(
            'UPDATE ' . Database::quote(self::TABLE) . ' SET ' . Database::quote('revoked_at') . ' = ?, '
            . Database::quote('updated_at') . ' = ? WHERE ' . Database::quote('token_hash') . ' = ? AND '
            . Database::quote('revoked_at') . ' IS NULL'
        );
        $statement->execute([Database::now(), Database::now(), hash('sha256', $token)]);
        Cookies::queue(self::COOKIE, '', 0, true);
        Cookies::queue(self::CSRF_COOKIE, '', 0, false);
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

<?php

declare(strict_types=1);

/** Cookies set while handling a request; the router adds them to the response. */
final class Cookies
{
    /** @var list<string> */
    private static array $pending = [];

    public static function queue(string $name, string $value, int $maxAge, bool $httpOnly): void
    {
        $parts = [$name . '=' . rawurlencode($value), 'Path=/', 'Max-Age=' . max(0, $maxAge), 'SameSite=Lax'];
        if ($httpOnly) {
            $parts[] = 'HttpOnly';
        }
        if (self::secure()) {
            $parts[] = 'Secure';
        }
        self::$pending[] = implode('; ', $parts);
    }

    /**
     * @return list<string> Set-Cookie header values
     */
    public static function flush(): array
    {
        $cookies = self::$pending;
        self::$pending = [];

        return $cookies;
    }

    private static function secure(): bool
    {
        $setting = strtolower((string) Env::get('SESSION_SECURE_COOKIE', ''));
        if ($setting === '') {
            return Env::get('APP_ENV', 'local') === 'production';
        }

        return in_array($setting, ['1', 'true', 'yes', 'on'], true);
    }
}

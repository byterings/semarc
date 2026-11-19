<?php

declare(strict_types=1);

/**
 * Converts database values into consistent JSON types for API responses.
 */
final class Cast
{
    public static function string(mixed $value): ?string
    {
        return $value === null ? null : (string) $value;
    }

    public static function int(mixed $value): ?int
    {
        return $value === null ? null : (int) $value;
    }

    public static function float(mixed $value): ?float
    {
        return $value === null ? null : (float) $value;
    }

    /** DECIMAL values are strings with exactly two decimals, whatever the database returns. */
    public static function decimal(mixed $value): ?string
    {
        return $value === null ? null : number_format((float) $value, 2, '.', '');
    }

    public static function bool(mixed $value): ?bool
    {
        if ($value === null) {
            return null;
        }
        if (is_string($value)) {
            return in_array(strtolower($value), ['1', 't', 'true'], true);
        }

        return (bool) $value;
    }

    public static function date(mixed $value): ?string
    {
        return $value === null ? null : substr((string) $value, 0, 10);
    }

    public static function timestamp(mixed $value): ?string
    {
        if ($value === null) {
            return null;
        }

        return str_replace(' ', 'T', substr((string) $value, 0, 19)) . 'Z';
    }
}

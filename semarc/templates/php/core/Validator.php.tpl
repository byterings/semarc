<?php

declare(strict_types=1);

/**
 * Validates request input against the field rules declared in the semantic
 * source (types, OPTIONAL, VALIDATE REQUIRED / EMAIL / MIN / MAX).
 */
final class Validator
{
    /**
     * @param array<string, mixed> $input
     * @param array<string, array<string, mixed>> $fields
     * @return array<string, mixed> validated values for known fields only
     */
    public function validate(array $input, array $fields, bool $partial = false): array
    {
        $errors = [];
        $clean = [];

        foreach ($fields as $name => $rules) {
            $present = array_key_exists($name, $input);
            $value = $present ? $input[$name] : null;

            if (!$present) {
                if (!$partial && $rules['required']) {
                    $errors[$name][] = "{$name} is required";
                }
                continue;
            }
            if ($value === null) {
                if ($rules['required']) {
                    $errors[$name][] = "{$name} is required";
                } else {
                    $clean[$name] = null;
                }
                continue;
            }

            $typeError = $this->typeError($name, $value, $rules['type']);
            if ($typeError !== null) {
                $errors[$name][] = $typeError;
                continue;
            }

            $ruleErrors = $this->ruleErrors($name, $value, $rules);
            if ($ruleErrors !== []) {
                $errors[$name] = $ruleErrors;
                continue;
            }

            $clean[$name] = match ($rules['type']) {
                'FLOAT' => (float) $value,
                'DATETIME' => self::utc((string) $value),
                default => $value,
            };
        }

        if ($errors !== []) {
            throw HttpException::validation($errors);
        }

        return $clean;
    }

    private function typeError(string $name, mixed $value, string $type): ?string
    {
        return match ($type) {
            'STRING', 'TEXT' => is_string($value) ? null : "{$name} must be a string",
            'INTEGER' => is_int($value) ? null : "{$name} must be an integer",
            'FLOAT' => is_int($value) || is_float($value) ? null : "{$name} must be a number",
            'BOOLEAN' => is_bool($value) ? null : "{$name} must be a boolean",
            'DATE' => self::isDate($value) ? null : "{$name} must be a date (YYYY-MM-DD)",
            'DATETIME' => self::isDateTime($value) ? null : "{$name} must be an ISO 8601 date and time",
            default => null,
        };
    }

    public static function isDate(mixed $value): bool
    {
        if (!is_string($value) || preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $value, $parts) !== 1) {
            return false;
        }

        return checkdate((int) $parts[2], (int) $parts[3], (int) $parts[1]);
    }

    public static function isDateTime(mixed $value): bool
    {
        if (!is_string($value)
            || preg_match('/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$/', $value) !== 1
            || !self::isDate(substr($value, 0, 10))) {
            return false;
        }
        [$hour, $minute, $second] = array_map('intval', explode(':', substr($value, 11, 8)));

        return $hour < 24 && $minute < 60 && $second < 60;
    }

    /** Converts an ISO 8601 value to the stored UTC form; values without an offset are UTC. */
    public static function utc(string $value): string
    {
        return (new DateTimeImmutable($value, new DateTimeZone('UTC')))
            ->setTimezone(new DateTimeZone('UTC'))
            ->format('Y-m-d H:i:s');
    }

    /**
     * @param array<string, mixed> $rules
     * @return list<string>
     */
    private function ruleErrors(string $name, mixed $value, array $rules): array
    {
        $errors = [];
        if (is_string($value)) {
            $length = mb_strlen($value);
            if ($rules['not_empty'] && trim($value) === '') {
                $errors[] = "{$name} must not be empty";
            }
            if ($rules['email'] && filter_var($value, FILTER_VALIDATE_EMAIL) === false) {
                $errors[] = "{$name} must be a valid email address";
            }
            if ($rules['min'] !== null && $length < $rules['min']) {
                $errors[] = "{$name} must be at least {$rules['min']} characters";
            }
            if ($rules['max'] !== null && $length > $rules['max']) {
                $errors[] = "{$name} must be at most {$rules['max']} characters";
            }
        } elseif (is_int($value) || is_float($value)) {
            if ($rules['min'] !== null && $value < $rules['min']) {
                $errors[] = "{$name} must be at least {$rules['min']}";
            }
            if ($rules['max'] !== null && $value > $rules['max']) {
                $errors[] = "{$name} must be at most {$rules['max']}";
            }
        }

        return $errors;
    }
}

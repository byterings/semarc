<?php

class {{class_name}}
{
    public function required(array $data, string $field): ?string
    {
        if (!isset($data[$field]) || trim((string) $data[$field]) === '') {
            return $field . ' is required';
        }

        return null;
    }

    public function email(array $data, string $field): ?string
    {
        if (!isset($data[$field]) || filter_var($data[$field], FILTER_VALIDATE_EMAIL)) {
            return null;
        }

        return $field . ' must be a valid email address';
    }

    public function minLength(array $data, string $field, int $length): ?string
    {
        if (!isset($data[$field]) || strlen((string) $data[$field]) >= $length) {
            return null;
        }

        return $field . ' must be at least ' . $length . ' characters';
    }

    public function validate(array $data, array $rules): array
    {
        $errors = [];

        foreach ($rules as $field => $fieldRules) {
            foreach ($fieldRules as $rule) {
                $error = $this->applyRule($data, $field, $rule);

                if ($error !== null) {
                    $errors[$field][] = $error;
                }
            }
        }

        return $errors;
    }

    private function applyRule(array $data, string $field, string $rule): ?string
    {
        if ($rule === 'required') {
            return $this->required($data, $field);
        }

        if ($rule === 'email') {
            return $this->email($data, $field);
        }

        if (str_starts_with($rule, 'min:')) {
            return $this->minLength($data, $field, (int) substr($rule, 4));
        }

        return null;
    }
}

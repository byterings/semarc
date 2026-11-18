<?php

declare(strict_types=1);

final class User
{
    public const TABLE = 'users';

    /** Declared fields and their validation rules. */
    public const FIELDS = [
        'email' => ['type' => 'STRING', 'required' => true, 'not_empty' => false, 'email' => false, 'min' => null, 'max' => 255],
        'name' => ['type' => 'STRING', 'required' => true, 'not_empty' => false, 'email' => false, 'min' => null, 'max' => 255],
        'password' => ['type' => 'STRING', 'required' => true, 'not_empty' => false, 'email' => false, 'min' => null, 'max' => 72],
    ];

    /** Foreign key columns and the model they reference. */
    public const REFERENCES = [];

    /** Tables whose rows reference this model; deletes are refused while they exist. */
    public const DEPENDENTS = [];

    public const UNIQUE = ['email'];

    public const HIDDEN = ['password'];

    /** Query parameters list routes accept as equality filters, with their types. */
    public const FILTERS = ['id' => 'INTEGER', 'email' => 'STRING', 'name' => 'STRING'];

    /** Fields list routes can sort by (?sort=field or ?sort=-field). */
    public const SORT = ['id', 'email', 'name', 'created_at', 'updated_at'];

    /**
     * @return array<string, array<string, mixed>>
     */
    public static function inputRules(?string $excludeColumn = null): array
    {
        $rules = self::FIELDS;
        foreach (self::REFERENCES as $column => $reference) {
            if ($column !== $excludeColumn) {
                $rules[$column] = ['type' => 'INTEGER', 'required' => true, 'not_empty' => false, 'email' => false, 'min' => 1, 'max' => null];
            }
        }

        return $rules;
    }

    /**
     * @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    public static function toArray(array $row): array
    {
        return [
            'id' => Cast::int($row['id']),
            'email' => Cast::string($row['email']),
            'name' => Cast::string($row['name']),
            'created_at' => Cast::timestamp($row['created_at']),
            'updated_at' => Cast::timestamp($row['updated_at']),
        ];
    }
}

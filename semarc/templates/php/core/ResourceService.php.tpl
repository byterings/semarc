<?php

declare(strict_types=1);

/**
 * Business rules shared by every generated resource: validation, uniqueness,
 * reference integrity, ownership and safe deletes. Model services extend this
 * class and can override beforeWrite() or add their own methods.
 */
abstract class ResourceService
{
    public const DEFAULT_LIMIT = {{default_limit}};
    public const MAX_LIMIT = {{max_limit}};

    protected Validator $validator;

    /**
     * @param class-string $model
     */
    public function __construct(
        protected readonly Repository $repository,
        protected readonly string $model,
    ) {
        $this->validator = new Validator();
    }

    /**
     * Lists records. $query holds request query parameters (equality filters and
     * sort); $where holds fixed conditions such as a parent id, which take precedence.
     *
     * @param array<string, mixed> $query
     * @param array<string, mixed> $where
     * @return array<string, mixed> data and pagination meta
     */
    public function list(int $limit, int $offset, array $query = [], array $where = []): array
    {
        $limit = max(1, min($limit, self::MAX_LIMIT));
        $offset = max(0, $offset);
        [$filters, $orderBy, $direction] = $this->parseQuery($query);
        $where += $filters;
        $rows = $this->repository->paginate($limit, $offset, $where, $orderBy, $direction);

        return [
            'data' => array_map([$this->model, 'toArray'], $rows),
            'meta' => ['total' => $this->repository->count($where), 'limit' => $limit, 'offset' => $offset],
        ];
    }

    /**
     * @return array<string, mixed> data and pagination meta
     */
    public function listForParent(
        string $parentModel,
        string $parentTable,
        string $column,
        int $parentId,
        int $limit,
        int $offset,
        array $query = [],
    ): array {
        if (!$this->repository->rowExists($parentTable, $parentId)) {
            throw HttpException::notFound("{$parentModel} {$parentId} not found.");
        }

        return $this->list($limit, $offset, $query, [$column => $parentId]);
    }

    /**
     * @return array<string, mixed>
     */
    public function get(int $id): array
    {
        return ($this->model)::toArray($this->find($id));
    }

    /**
     * @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function create(array $input, ?int $ownerId = null): array
    {
        $owner = $this->ownerColumn($ownerId);
        $data = $this->validator->validate($input, ($this->model)::inputRules($owner), false);
        if ($owner !== null) {
            $data[$owner] = $ownerId;
        }
        $data += ($this->model)::DEFAULTS;

        $this->assertReferencesExist($data);
        $this->assertUnique($data, null);

        return ($this->model)::toArray($this->repository->create($this->beforeWrite($data)));
    }

    /**
     * @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function update(int $id, array $input, bool $partial, ?int $ownerId = null, bool $manageAll = false): array
    {
        $record = $this->find($id);
        if (!$manageAll) {
            $this->assertOwner($record, $ownerId);
        }
        $owner = $this->ownerColumn($ownerId);
        $data = $this->validator->validate($input, ($this->model)::inputRules($owner), $partial);
        if ($data === []) {
            return $this->get($id);
        }

        $this->assertReferencesExist($data);
        $this->assertUnique($data, $id);

        return ($this->model)::toArray($this->repository->update($id, $this->beforeWrite($data)));
    }

    public function delete(int $id, ?int $ownerId = null, bool $manageAll = false): void
    {
        $record = $this->find($id);
        if (!$manageAll) {
            $this->assertOwner($record, $ownerId);
        }
        foreach (($this->model)::DEPENDENTS as $dependent) {
            if ($this->repository->countIn($dependent['table'], $dependent['column'], $id) > 0) {
                throw HttpException::conflict(
                    "Cannot delete {$this->name()} {$id} while {$dependent['model']} records reference it."
                );
            }
        }
        $this->repository->delete($id);
    }

    /**
     * Hook for model specific changes before data is stored.
     *
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    protected function beforeWrite(array $data): array
    {
        return $data;
    }

    /**
     * @return array<string, mixed>
     */
    protected function find(int $id): array
    {
        return $this->repository->findById($id) ?? throw HttpException::notFound("{$this->name()} {$id} not found.");
    }

    /**
     * @param array<string, mixed> $query
     * @return array{0: array<string, mixed>, 1: string, 2: string}
     */
    private function parseQuery(array $query): array
    {
        $errors = [];
        $filters = [];
        foreach (($this->model)::FILTERS as $field => $type) {
            if (!array_key_exists($field, $query)) {
                continue;
            }
            $value = is_string($query[$field]) ? self::filterValue($query[$field], $type) : null;
            if ($value === null) {
                $errors[$field][] = "{$field} filter must be " . self::describe($type);
                continue;
            }
            $filters[$field] = $value;
        }

        $orderBy = 'id';
        $direction = 'ASC';
        if (array_key_exists('sort', $query)) {
            $sort = is_string($query['sort']) ? $query['sort'] : '';
            $field = ltrim($sort, '-');
            if (!in_array($field, ($this->model)::SORT, true)) {
                $errors['sort'][] = 'sort must be one of: ' . implode(', ', ($this->model)::SORT) . ' (prefix with - for descending)';
            } else {
                $orderBy = $field;
                $direction = str_starts_with($sort, '-') ? 'DESC' : 'ASC';
            }
        }

        if ($errors !== []) {
            throw HttpException::validation($errors);
        }

        return [$filters, $orderBy, $direction];
    }

    private static function filterValue(string $raw, string $type): mixed
    {
        return match ($type) {
            'INTEGER' => preg_match('/^-?\d+$/', $raw) === 1 ? (int) $raw : null,
            'FLOAT' => is_numeric($raw) ? (float) $raw : null,
            'BOOLEAN' => match (strtolower($raw)) {
                'true', '1' => true,
                'false', '0' => false,
                default => null,
            },
            'DATE' => Validator::isDate($raw) ? $raw : null,
            default => $raw,
        };
    }

    private static function describe(string $type): string
    {
        return match ($type) {
            'INTEGER' => 'an integer',
            'FLOAT' => 'a number',
            'BOOLEAN' => 'true or false',
            'DATE' => 'a date (YYYY-MM-DD)',
            default => 'text',
        };
    }

    /**
     * On protected routes, records with an owner column may only be changed by their owner.
     *
     * @param array<string, mixed> $record
     */
    private function assertOwner(array $record, ?int $ownerId): void
    {
        $column = $this->ownerColumn($ownerId);
        if ($column !== null && (int) $record[$column] !== $ownerId) {
            throw HttpException::forbidden("Only the owner can modify this {$this->name()}.");
        }
    }

    private function ownerColumn(?int $ownerId): ?string
    {
        if ($ownerId === null) {
            return null;
        }
        foreach (($this->model)::REFERENCES as $column => $reference) {
            if ($reference['owner']) {
                return $column;
            }
        }

        return null;
    }

    /**
     * @param array<string, mixed> $data
     */
    private function assertReferencesExist(array $data): void
    {
        $errors = [];
        foreach (($this->model)::REFERENCES as $column => $reference) {
            if (isset($data[$column]) && !$this->repository->rowExists($reference['table'], (int) $data[$column])) {
                $errors[$column][] = "{$column} does not reference an existing {$reference['model']}";
            }
        }
        if ($errors !== []) {
            throw HttpException::validation($errors);
        }
    }

    /**
     * @param array<string, mixed> $data
     */
    private function assertUnique(array $data, ?int $exceptId): void
    {
        $errors = [];
        foreach (($this->model)::UNIQUE as $column) {
            if (array_key_exists($column, $data) && $data[$column] !== null
                && $this->repository->existsWhere($column, $data[$column], $exceptId)) {
                $errors[$column][] = "{$column} has already been taken";
            }
        }
        if ($errors !== []) {
            throw HttpException::conflict("{$this->name()} already exists.", $errors);
        }
    }

    private function name(): string
    {
        return $this->model;
    }
}

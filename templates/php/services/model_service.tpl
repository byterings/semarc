<?php

require_once __DIR__ . '/../repositories/{{repository_name}}.php';

class {{service_name}}
{
    private {{repository_name}} $repository;

    public function __construct()
    {
        $this->repository = new {{repository_name}}();
    }

    public function list(): array
    {
        return $this->repository->{{list_method}}();
    }

    public function create(array $data): array
    {
        return $this->repository->{{create_method}}($data);
    }
}

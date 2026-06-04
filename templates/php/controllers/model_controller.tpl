<?php

require_once __DIR__ . '/../services/{{service_name}}.php';

class {{controller_name}}
{
    private {{service_name}} $service;

    public function __construct()
    {
        $this->service = new {{service_name}}();
    }

    public function index(): void
    {
        header('Content-Type: application/json');
        echo json_encode(['data' => $this->service->list()]);
    }

    public function store(): void
    {
        header('Content-Type: application/json');
        $input = json_decode(file_get_contents('php://input'), true) ?? [];
        http_response_code(202);
        echo json_encode([
            'status' => 'accepted',
            'data' => $this->service->create($input),
            'note' => 'Persistence implementation is a generated TODO scaffold.',
        ]);
    }
}

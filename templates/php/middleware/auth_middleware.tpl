<?php

require_once __DIR__ . '/../services/{{token_service_class}}.php';

class {{class_name}}
{
    private {{token_service_class}} $tokens;

    public function __construct()
    {
        $this->tokens = new {{token_service_class}}();
    }

    public function handle(): ?array
    {
        // TODO: connect this middleware to a real authentication provider.
        $this->reject();
        return null;
    }

    private function extractBearerToken(string $header): ?string
    {
        if (!str_starts_with($header, 'Bearer ')) {
            return null;
        }

        return trim(substr($header, 7));
    }

    private function reject(): void
    {
        http_response_code(401);
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Unauthorized']);
    }
}

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
        $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        $token = $this->extractBearerToken($header);

        if ($token === null) {
            $this->reject();
            return null;
        }

        $payload = $this->tokens->validate($token);

        if ($payload === null) {
            $this->reject();
            return null;
        }

        return $payload;
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

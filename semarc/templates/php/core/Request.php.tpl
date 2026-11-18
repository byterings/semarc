<?php

declare(strict_types=1);

final class Request
{
    public ?int $userId = null;

    private ?array $decoded = null;

    /**
     * @param array<string, mixed> $query
     * @param array<string, string> $headers
     */
    public function __construct(
        public readonly string $method,
        public readonly string $path,
        public readonly array $query = [],
        public readonly array $headers = [],
        private readonly string $body = '',
        public readonly string $ip = '127.0.0.1',
    ) {
    }

    public static function capture(): self
    {
        $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
        $headers = [];
        foreach ($_SERVER as $key => $value) {
            if (str_starts_with($key, 'HTTP_')) {
                $headers[strtolower(str_replace('_', '-', substr($key, 5)))] = (string) $value;
            }
        }
        if (!isset($headers['authorization']) && isset($_SERVER['REDIRECT_HTTP_AUTHORIZATION'])) {
            $headers['authorization'] = (string) $_SERVER['REDIRECT_HTTP_AUTHORIZATION'];
        }

        return new self(
            strtoupper($_SERVER['REQUEST_METHOD'] ?? 'GET'),
            self::normalizePath($path),
            $_GET,
            $headers,
            (string) file_get_contents('php://input'),
            (string) ($_SERVER['REMOTE_ADDR'] ?? ''),
        );
    }

    public static function normalizePath(string $path): string
    {
        $trimmed = rtrim($path, '/');
        return $trimmed === '' ? '/' : $trimmed;
    }

    /**
     * @return array<string, mixed>
     */
    public function json(): array
    {
        if ($this->decoded !== null) {
            return $this->decoded;
        }
        if (trim($this->body) === '') {
            return $this->decoded = [];
        }

        $decoded = json_decode($this->body, true);
        if (!is_array($decoded) || ($decoded !== [] && array_is_list($decoded))) {
            throw HttpException::badRequest('Request body must be a JSON object.');
        }

        return $this->decoded = $decoded;
    }

    public function header(string $name): ?string
    {
        return $this->headers[strtolower($name)] ?? null;
    }

    public function bearerToken(): ?string
    {
        $header = $this->header('authorization');
        if ($header === null || preg_match('/^Bearer\s+(\S+)$/i', $header, $matches) !== 1) {
            return null;
        }

        return $matches[1];
    }

    public function queryInt(string $key, int $default): int
    {
        $value = $this->query[$key] ?? null;
        if (!is_string($value) || preg_match('/^\d+$/', $value) !== 1) {
            return $default;
        }

        return (int) $value;
    }
}

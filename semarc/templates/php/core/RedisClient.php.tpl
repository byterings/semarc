<?php

declare(strict_types=1);

/** Minimal Redis client (RESP over TCP or TLS) for redis:// and rediss:// URLs. */
final class RedisClient
{
    /** @var resource */
    private $socket;

    public function __construct(string $url)
    {
        $parts = parse_url($url);
        if ($parts === false || !in_array($parts['scheme'] ?? '', ['redis', 'rediss'], true)) {
            throw new RuntimeException('REDIS_URL must be a redis:// or rediss:// URL.');
        }
        $transport = $parts['scheme'] === 'rediss' ? 'tls' : 'tcp';
        $address = $transport . '://' . ($parts['host'] ?? '127.0.0.1') . ':' . ($parts['port'] ?? 6379);
        $socket = @stream_socket_client($address, $errorCode, $errorMessage, 2.0);
        if ($socket === false) {
            throw new RuntimeException("Cannot connect to Redis: {$errorMessage}");
        }
        stream_set_timeout($socket, 2);
        $this->socket = $socket;

        if (isset($parts['pass'])) {
            $credentials = isset($parts['user']) && $parts['user'] !== '' ? [rawurldecode($parts['user']), rawurldecode($parts['pass'])] : [rawurldecode($parts['pass'])];
            $this->command('AUTH', ...$credentials);
        }
        $database = trim($parts['path'] ?? '', '/');
        if ($database !== '' && $database !== '0') {
            $this->command('SELECT', $database);
        }
    }

    public function command(string ...$arguments): mixed
    {
        $payload = '*' . count($arguments) . "\r\n";
        foreach ($arguments as $argument) {
            $payload .= '$' . strlen($argument) . "\r\n" . $argument . "\r\n";
        }
        if (fwrite($this->socket, $payload) === false) {
            throw new RuntimeException('Cannot write to Redis.');
        }

        return $this->read();
    }

    private function read(): mixed
    {
        $line = fgets($this->socket);
        if ($line === false) {
            throw new RuntimeException('Redis did not answer.');
        }
        $value = substr($line, 1, -2);

        return match ($line[0]) {
            '+' => $value,
            ':' => (int) $value,
            '-' => throw new RuntimeException('Redis error: ' . $value),
            '$' => $value === '-1' ? null : substr((string) stream_get_contents($this->socket, (int) $value + 2), 0, -2),
            '*' => $value === '-1' ? null : array_map(fn (): mixed => $this->read(), array_fill(0, (int) $value, null)),
            default => throw new RuntimeException('Unexpected Redis reply.'),
        };
    }
}

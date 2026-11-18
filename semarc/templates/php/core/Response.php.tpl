<?php

declare(strict_types=1);

final class Response
{
    /**
     * @param array<string, string> $headers
     * @param list<string> $cookies Set-Cookie header values
     */
    public function __construct(
        public readonly int $status,
        public readonly mixed $body,
        public readonly string $contentType = 'application/json',
        public readonly array $headers = [],
        public readonly array $cookies = [],
    ) {
    }

    /**
     * @param array<string, string> $headers
     */
    public function withHeaders(array $headers): self
    {
        return new self($this->status, $this->body, $this->contentType, $headers + $this->headers, $this->cookies);
    }

    /**
     * @param list<string> $cookies Set-Cookie header values
     */
    public function withCookies(array $cookies): self
    {
        return new self($this->status, $this->body, $this->contentType, $this->headers, [...$this->cookies, ...$cookies]);
    }

    public function header(string $name): ?string
    {
        foreach ($this->headers as $key => $value) {
            if (strcasecmp($key, $name) === 0) {
                return $value;
            }
        }

        return null;
    }

    public static function json(mixed $body, int $status = 200): self
    {
        return new self($status, $body);
    }

    public static function html(string $body, int $status = 200): self
    {
        return new self($status, $body, 'text/html; charset=utf-8');
    }

    /** A pre-rendered body, such as a JSON or HTML file, sent as-is. */
    public static function file(string $content, string $contentType): self
    {
        return new self(200, $content, $contentType);
    }

    public static function noContent(): self
    {
        return new self(204, null);
    }

    public static function error(HttpException $exception): self
    {
        $error = [
            'code' => $exception->errorCode,
            'message' => $exception->getMessage(),
        ];
        if ($exception->details !== []) {
            $error['details'] = $exception->details;
        }

        return self::json(['error' => $error], $exception->status)->withHeaders($exception->headers);
    }

    public function content(): string
    {
        if ($this->body === null) {
            return '';
        }
        if (is_string($this->body) && $this->contentType !== 'application/json') {
            return $this->body;
        }

        return (string) json_encode($this->body, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION);
    }

    public function send(): void
    {
        http_response_code($this->status);
        foreach ($this->headers as $name => $value) {
            header($name . ': ' . $value);
        }
        foreach ($this->cookies as $cookie) {
            header('Set-Cookie: ' . $cookie, false);
        }
        if ($this->status !== 204) {
            header('Content-Type: ' . $this->contentType);
            echo $this->content();
        }
    }
}

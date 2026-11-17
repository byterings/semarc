<?php

declare(strict_types=1);

final class HttpException extends RuntimeException
{
    /**
     * @param array<string, list<string>> $details
     */
    public function __construct(
        public readonly int $status,
        public readonly string $errorCode,
        string $message,
        public readonly array $details = [],
    ) {
        parent::__construct($message);
    }

    public static function badRequest(string $message): self
    {
        return new self(400, 'bad_request', $message);
    }

    public static function unauthorized(string $message = 'Authentication required.'): self
    {
        return new self(401, 'unauthorized', $message);
    }

    public static function forbidden(string $message): self
    {
        return new self(403, 'forbidden', $message);
    }

    public static function notFound(string $message = 'Resource not found.'): self
    {
        return new self(404, 'not_found', $message);
    }

    public static function conflict(string $message, array $details = []): self
    {
        return new self(409, 'conflict', $message, $details);
    }

    /**
     * @param array<string, list<string>> $details
     */
    public static function validation(array $details): self
    {
        return new self(422, 'validation_failed', 'The given data was invalid.', $details);
    }

    public static function notImplemented(string $message): self
    {
        return new self(501, 'not_implemented', $message);
    }
}

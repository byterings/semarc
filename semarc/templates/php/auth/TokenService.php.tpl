<?php

declare(strict_types=1);

final class TokenService
{
    public const MIN_SECRET_LENGTH = 32;

    /**
     * @return array{access_token: string, token_type: string, expires_in: int}
     */
    public function issue(int $userId): array
    {
        $ttl = (int) Env::get('JWT_TTL', '{{token_ttl}}');
        $now = time();

        return [
            'access_token' => Jwt::encode(['sub' => (string) $userId, 'iat' => $now, 'exp' => $now + $ttl], $this->secret()),
            'token_type' => 'Bearer',
            'expires_in' => $ttl,
        ];
    }

    public function userIdFrom(string $token): int
    {
        try {
            $claims = Jwt::decode($token, $this->secret());
        } catch (InvalidArgumentException $exception) {
            throw HttpException::unauthorized($exception->getMessage());
        }

        $subject = $claims['sub'] ?? null;
        if (!is_string($subject) || preg_match('/^[1-9]\d*$/', $subject) !== 1) {
            throw HttpException::unauthorized('Invalid token subject.');
        }

        return (int) $subject;
    }

    private function secret(): string
    {
        $secret = Env::get('JWT_SECRET');
        if ($secret === null || strlen($secret) < self::MIN_SECRET_LENGTH) {
            throw new RuntimeException('JWT_SECRET must be set to at least ' . self::MIN_SECRET_LENGTH . ' characters.');
        }

        return $secret;
    }
}

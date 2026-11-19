<?php

declare(strict_types=1);

/**
 * Minimal HS256 JSON Web Token implementation (RFC 7519) using hash_hmac.
 */
final class Jwt
{
    /**
     * @param array<string, mixed> $claims
     */
    public static function encode(array $claims, string $secret): string
    {
        $header = self::base64UrlEncode((string) json_encode(['alg' => 'HS256', 'typ' => 'JWT']));
        $payload = self::base64UrlEncode((string) json_encode($claims));
        $signature = self::base64UrlEncode(hash_hmac('sha256', $header . '.' . $payload, $secret, true));

        return $header . '.' . $payload . '.' . $signature;
    }

    /**
     * @return array<string, mixed>
     */
    public static function decode(string $token, string $secret, ?int $now = null): array
    {
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            throw new InvalidArgumentException('Malformed token.');
        }
        [$header, $payload, $signature] = $parts;

        $decodedHeader = json_decode(self::base64UrlDecode($header), true);
        if (!is_array($decodedHeader) || ($decodedHeader['alg'] ?? null) !== 'HS256') {
            throw new InvalidArgumentException('Unsupported token algorithm.');
        }

        $expected = self::base64UrlEncode(hash_hmac('sha256', $header . '.' . $payload, $secret, true));
        if (!hash_equals($expected, $signature)) {
            throw new InvalidArgumentException('Invalid token signature.');
        }

        $claims = json_decode(self::base64UrlDecode($payload), true);
        if (!is_array($claims)) {
            throw new InvalidArgumentException('Malformed token payload.');
        }
        if (!isset($claims['exp']) || !is_int($claims['exp']) || $claims['exp'] <= ($now ?? time())) {
            throw new InvalidArgumentException('Token has expired.');
        }

        return $claims;
    }

    private static function base64UrlEncode(string $value): string
    {
        return rtrim(strtr(base64_encode($value), '+/', '-_'), '=');
    }

    private static function base64UrlDecode(string $value): string
    {
        $decoded = base64_decode(strtr($value, '-_', '+/') . str_repeat('=', (4 - strlen($value) % 4) % 4), true);
        if ($decoded === false) {
            throw new InvalidArgumentException('Malformed token encoding.');
        }

        return $decoded;
    }
}

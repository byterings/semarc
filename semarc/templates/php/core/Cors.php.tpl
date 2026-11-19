<?php

declare(strict_types=1);

/**
 * Cross-origin resource sharing for browser clients. CORS_ORIGINS is a comma
 * separated list of allowed origins, or * (the default) to allow any origin.
 */
final class Cors
{
    private const ALLOWED_METHODS = 'GET, POST, PUT, PATCH, DELETE, OPTIONS';
    private const ALLOWED_HEADERS = 'Authorization, Content-Type, X-CSRF-Token';
    /** Cookie sessions need credentials; they are allowed only for listed origins, never for *. */
    private const ALLOW_CREDENTIALS = {{allow_credentials}};

    public static function isPreflight(Request $request): bool
    {
        return $request->method === 'OPTIONS' && $request->header('access-control-request-method') !== null;
    }

    public static function preflight(Request $request): Response
    {
        $response = self::apply($request, Response::noContent());
        if ($response->header('Access-Control-Allow-Origin') === null) {
            return $response;
        }

        return $response->withHeaders([
            'Access-Control-Allow-Methods' => self::ALLOWED_METHODS,
            'Access-Control-Allow-Headers' => self::ALLOWED_HEADERS,
            'Access-Control-Max-Age' => '600',
        ]);
    }

    public static function apply(Request $request, Response $response): Response
    {
        $origin = $request->header('origin');
        if ($origin === null) {
            return $response;
        }

        $allowed = array_values(array_filter(array_map('trim', explode(',', (string) Env::get('CORS_ORIGINS', '*')))));
        if (in_array('*', $allowed, true)) {
            return $response->withHeaders(['Access-Control-Allow-Origin' => '*']);
        }
        if (in_array($origin, $allowed, true)) {
            $headers = ['Access-Control-Allow-Origin' => $origin, 'Vary' => 'Origin'];
            if (self::ALLOW_CREDENTIALS) {
                $headers['Access-Control-Allow-Credentials'] = 'true';
            }

            return $response->withHeaders($headers);
        }

        return $response;
    }
}

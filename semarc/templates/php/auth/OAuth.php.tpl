<?php

declare(strict_types=1);

/**
 * Sign-in with OAuth providers (authorization code flow).
 *
 * GET /oauth/<provider> returns the provider authorization URL and a signed `state`. The
 * front end sends the user there; the provider redirects back to OAUTH_<PROVIDER>_REDIRECT_URI
 * with `code` and `state`, which the front end posts to POST /oauth/<provider>/callback. The
 * front end must check that the returned `state` equals the one it received.
 */
final class OAuth
{
    private const STATE_TTL_SECONDS = {{state_ttl}};
    private const TIMEOUT_SECONDS = 10;
    private const MIN_SECRET_LENGTH = 32;
    private const TABLE = '{{table}}';

    /** @var array<string, array<string, mixed>> endpoints and profile fields per provider */
    private const PROVIDERS = {{providers}};

    /**
     * @return array{authorization_url: string, state: string}
     */
    public static function start(string $provider): array
    {
        $config = self::config($provider);
        $details = self::PROVIDERS[$provider];
        $payload = $provider . '.' . (time() + self::STATE_TTL_SECONDS) . '.' . bin2hex(random_bytes(16));
        $state = $payload . '.' . self::signature($payload);
        $query = http_build_query([
            'response_type' => 'code',
            'client_id' => $config['client_id'],
            'redirect_uri' => $config['redirect_uri'],
            'scope' => implode(' ', $details['scopes']),
            'state' => $state,
        ], '', '&', PHP_QUERY_RFC3986);

        return ['authorization_url' => self::url($config, $details['authorize_url']) . '?' . $query, 'state' => $state];
    }

    public static function verifyState(string $provider, string $state): void
    {
        $parts = explode('.', $state);
        $valid = count($parts) === 4
            && $parts[0] === $provider
            && ctype_digit($parts[1])
            && (int) $parts[1] > time()
            && hash_equals(self::signature(implode('.', array_slice($parts, 0, 3))), $parts[3]);
        if (!$valid) {
            throw HttpException::validation(['state' => ['state is invalid or expired']]);
        }
    }

    /**
     * Exchanges the code and returns the provider subject, verified email and display name.
     *
     * @return array{subject: string, email: string, name: string}
     */
    public static function fetchIdentity(string $provider, string $code): array
    {
        $config = self::config($provider);
        $details = self::PROVIDERS[$provider];
        $tokens = self::request($provider, self::url($config, $details['token_url']), [
            'grant_type' => 'authorization_code',
            'code' => $code,
            'redirect_uri' => $config['redirect_uri'],
            'client_id' => $config['client_id'],
            'client_secret' => $config['client_secret'],
        ]);
        $accessToken = is_array($tokens) ? ($tokens['access_token'] ?? null) : null;
        if (!is_string($accessToken) || $accessToken === '') {
            throw HttpException::validation(['code' => ['code is invalid or expired']]);
        }

        $profile = self::request($provider, self::url($config, $details['profile_url']), null, $accessToken);
        $subject = is_array($profile) ? ($profile[$details['subject_field']] ?? null) : null;
        if ($subject === null || $subject === '' || is_array($subject)) {
            throw new HttpException(502, 'bad_gateway', "OAuth provider {$provider} returned an unexpected profile.");
        }
        $email = null;
        if ($details['emails_url'] !== null) {
            $addresses = self::request($provider, self::url($config, $details['emails_url']), null, $accessToken);
            foreach (is_array($addresses) ? $addresses : [] as $address) {
                if (is_array($address) && ($address['primary'] ?? null) === true && ($address['verified'] ?? null) === true) {
                    $email = $address['email'] ?? null;
                }
            }
        } elseif (($profile[$details['verified_field']] ?? null) === true) {
            $email = $profile[$details['email_field']] ?? null;
        }
        if (!is_string($email) || !str_contains($email, '@')) {
            throw HttpException::validation(['email' => ["{$provider} did not confirm a verified email address"]]);
        }

        $name = $profile[$details['name_field']] ?? null;
        if (!is_string($name) || trim($name) === '') {
            $name = explode('@', $email)[0];
        }

        return ['subject' => $provider . ':' . $subject, 'email' => $email, 'name' => trim($name)];
    }

    public static function findUserId(string $subject): ?int
    {
        $statement = Database::connection()->prepare(
            'SELECT ' . Database::quote('user_id') . ' FROM ' . Database::quote(self::TABLE)
            . ' WHERE ' . Database::quote('provider_subject') . ' = ? LIMIT 1'
        );
        $statement->execute([$subject]);
        $userId = $statement->fetchColumn();

        return $userId === false ? null : (int) $userId;
    }

    public static function link(string $provider, string $subject, int $userId): void
    {
        $now = Database::now();
        $statement = Database::connection()->prepare(
            'INSERT INTO ' . Database::quote(self::TABLE) . ' ('
            . implode(', ', array_map([Database::class, 'quote'], ['provider', 'provider_subject', 'user_id', 'created_at', 'updated_at']))
            . ') VALUES (?, ?, ?, ?, ?)'
        );
        $statement->execute([$provider, $subject, $userId, $now, $now]);
    }

    /**
     * @return array{client_id: string, client_secret: string, redirect_uri: string, endpoint: ?string}
     */
    private static function config(string $provider): array
    {
        $prefix = 'OAUTH_' . strtoupper($provider);
        $config = [
            'client_id' => (string) Env::get($prefix . '_CLIENT_ID', ''),
            'client_secret' => (string) Env::get($prefix . '_CLIENT_SECRET', ''),
            'redirect_uri' => (string) Env::get($prefix . '_REDIRECT_URI', ''),
            'endpoint' => Env::get($prefix . '_ENDPOINT'),
        ];
        if ($config['client_id'] === '' || $config['client_secret'] === '' || $config['redirect_uri'] === '') {
            throw new HttpException(503, 'service_unavailable', "OAuth provider {$provider} is not configured.");
        }

        return $config;
    }

    /** OAUTH_<PROVIDER>_ENDPOINT replaces the provider origin (used with a mock provider in tests). */
    private static function url(array $config, string $url): string
    {
        if ($config['endpoint'] === null || $config['endpoint'] === '') {
            return $url;
        }
        $endpoint = parse_url($config['endpoint']);
        $path = (string) parse_url($url, PHP_URL_PATH);

        return $endpoint['scheme'] . '://' . $endpoint['host'] . (isset($endpoint['port']) ? ':' . $endpoint['port'] : '') . $path;
    }

    private static function signature(string $payload): string
    {
        $secret = (string) Env::get('JWT_SECRET', '');
        if (strlen($secret) < self::MIN_SECRET_LENGTH) {
            throw new RuntimeException('JWT_SECRET must be set to at least ' . self::MIN_SECRET_LENGTH . ' characters.');
        }

        return hash_hmac('sha256', 'oauth-state:' . $payload, $secret);
    }

    /**
     * @param array<string, string>|null $form POSTs the form when given, GETs otherwise
     */
    private static function request(string $provider, string $url, ?array $form, ?string $token = null): mixed
    {
        $headers = ['Accept: application/json', 'User-Agent: ' . Env::get('APP_NAME', 'semarc-app')];
        if ($token !== null) {
            $headers[] = 'Authorization: Bearer ' . $token;
        }
        $options = ['method' => 'GET', 'timeout' => self::TIMEOUT_SECONDS, 'ignore_errors' => true];
        if ($form !== null) {
            $headers[] = 'Content-Type: application/x-www-form-urlencoded';
            $options['method'] = 'POST';
            $options['content'] = http_build_query($form, '', '&');
        }
        $options['header'] = implode("\r\n", $headers);

        $body = @file_get_contents($url, false, stream_context_create(['http' => $options]));
        $status = 0;
        foreach ($http_response_header ?? [] as $line) {
            if (preg_match('#^HTTP/\S+\s+(\d{3})#', $line, $matches) === 1) {
                $status = (int) $matches[1];
            }
        }
        if ($body === false || $status === 0) {
            throw new HttpException(502, 'bad_gateway', "OAuth provider {$provider} is unavailable.");
        }
        if ($status >= 400) {
            if ($form !== null && $status < 500) {
                throw HttpException::validation(['code' => ['code is invalid or expired']]);
            }
            throw new HttpException(502, 'bad_gateway', "OAuth provider {$provider} returned an error.");
        }
        try {
            return json_decode($body, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException) {
            throw new HttpException(502, 'bad_gateway', "OAuth provider {$provider} returned invalid JSON.");
        }
    }
}

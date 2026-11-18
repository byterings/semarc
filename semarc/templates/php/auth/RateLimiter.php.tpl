<?php

declare(strict_types=1);

/**
 * Fixed-window rate limiting for authentication endpoints. Counters are kept in
 * files (with locking) because PHP handles every request in a fresh process.
 */
final class RateLimiter
{
    public function __construct(
        private readonly string $directory,
        private readonly int $attempts,
        private readonly int $windowSeconds,
    ) {
    }

    public static function forAuth(): self
    {
        return new self(
            (string) Env::get('RATE_LIMIT_STORAGE', dirname(__DIR__) . '/storage/rate-limits'),
            (int) Env::get('AUTH_RATE_LIMIT', '{{attempts}}'),
            (int) Env::get('AUTH_RATE_WINDOW', '{{window}}'),
        );
    }

    /** Counts an attempt for $key and answers 429 once the limit is exceeded. */
    public function hit(string $key): void
    {
        if (!is_dir($this->directory) && !mkdir($this->directory, 0775, true) && !is_dir($this->directory)) {
            throw new RuntimeException("Cannot create rate limit storage: {$this->directory}");
        }

        $handle = fopen($this->directory . '/' . sha1($key) . '.json', 'c+');
        if ($handle === false) {
            throw new RuntimeException('Cannot open rate limit storage.');
        }

        $now = time();
        try {
            flock($handle, LOCK_EX);
            $state = json_decode((string) stream_get_contents($handle), true);
            if (!is_array($state) || ($state['reset'] ?? 0) <= $now) {
                $state = ['count' => 0, 'reset' => $now + $this->windowSeconds];
            }
            $state['count']++;
            ftruncate($handle, 0);
            rewind($handle);
            fwrite($handle, (string) json_encode($state));
        } finally {
            flock($handle, LOCK_UN);
            fclose($handle);
        }

        if ($state['count'] > $this->attempts) {
            $retry = max(1, $state['reset'] - $now);
            throw new HttpException(
                429,
                'too_many_requests',
                "Too many attempts. Try again in {$retry} seconds.",
                [],
                ['Retry-After' => (string) $retry],
            );
        }
    }
}

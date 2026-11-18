<?php

declare(strict_types=1);

/**
 * Fixed-window rate limiting for authentication endpoints. With RATE_LIMIT_STORE=redis the
 * counters live in Redis (shared by every server); otherwise, or when Redis cannot be
 * reached, in files (with locking) because PHP handles every request in a fresh process.
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
        [$count, $retry] = $this->count($key);
        if ($count > $this->attempts) {
            throw new HttpException(
                429,
                'too_many_requests',
                "Too many attempts. Try again in {$retry} seconds.",
                [],
                ['Retry-After' => (string) max(1, $retry)],
            );
        }
    }

    /**
     * @return array{0: int, 1: int} attempts in the current window and seconds until it ends
     */
    private function count(string $key): array
    {
        if (Env::get('RATE_LIMIT_STORE', 'local') === 'redis') {
            try {
                $redis = new RedisClient((string) Env::get('REDIS_URL', 'redis://127.0.0.1:6379/0'));
                $name = 'semarc:rate-limit:' . sha1($key);
                $redis->command('SET', $name, '0', 'EX', (string) $this->windowSeconds, 'NX');
                $count = (int) $redis->command('INCR', $name);

                return [$count, (int) $redis->command('TTL', $name)];
            } catch (RuntimeException $exception) {
                error_log('Rate limiting falls back to local storage: ' . $exception->getMessage());
            }
        }

        return $this->countLocally($key);
    }

    /**
     * @return array{0: int, 1: int}
     */
    private function countLocally(string $key): array
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

        return [$state['count'], $state['reset'] - $now];
    }
}

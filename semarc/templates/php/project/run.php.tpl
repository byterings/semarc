<?php

declare(strict_types=1);

// Replays tests/api_scenario.json against the application in-process,
// using a fresh in-memory SQLite database. Run: php tests/run.php

putenv('DB_CONNECTION=sqlite');
putenv('DB_DATABASE=:memory:');
putenv('BOOTSTRAP_ADMIN_EMAIL=admin@example.com');
putenv('RATE_LIMIT_STORAGE=' . sys_get_temp_dir() . '/semarc-rate-limits-' . bin2hex(random_bytes(6)));
if (getenv('JWT_SECRET') === false) {
    putenv('JWT_SECRET=semarc-test-secret-semarc-test-secret');
}

require_once __DIR__ . '/../bootstrap.php';

(new Migrator(Database::connection(), __DIR__ . '/../migrations'))->run();
/** @var Router $router */
$router = require __DIR__ . '/../routes.php';
$scenario = json_decode((string) file_get_contents(__DIR__ . '/api_scenario.json'), true, 512, JSON_THROW_ON_ERROR);

$missing = new stdClass();
$dig = static function (mixed $data, string $path) use ($missing): mixed {
    foreach (explode('.', $path) as $key) {
        if (!is_array($data) || !array_key_exists($key, $data)) {
            return $missing;
        }
        $data = $data[$key];
    }

    return $data;
};
$resolve = static function (mixed $value, array $vars) use (&$resolve): mixed {
    if (is_array($value)) {
        if (array_keys($value) === ['$ref']) {
            return $vars[$value['$ref']] ?? null;
        }

        return array_map(static fn (mixed $item): mixed => $resolve($item, $vars), $value);
    }

    return $value;
};

$vars = [];
$passed = 0;
foreach ($scenario['steps'] as $step) {
    $path = preg_replace_callback('/\$\{(\w+)\}/', static fn (array $m): string => (string) ($vars[$m[1]] ?? ''), $step['path']);
    $headers = ['content-type' => 'application/json'];
    foreach ($step['headers'] ?? [] as $name => $value) {
        $headers[strtolower($name)] = $value;
    }
    if (!empty($step['auth'])) {
        $headers['authorization'] = 'Bearer ' . ($vars[$step['auth_as'] ?? 'token'] ?? '');
    }
    if (isset($step['token'])) {
        $headers['authorization'] = 'Bearer ' . $step['token'];
    }
    $body = array_key_exists('body', $step) ? (string) json_encode($resolve($step['body'], $vars)) : '';
    if ($body === '[]') {
        $body = '{}';
    }

    $query = [];
    parse_str((string) parse_url($path, PHP_URL_QUERY), $query);
    $route = (string) parse_url($path, PHP_URL_PATH);
    $response = $router->dispatch(new Request($step['method'], Request::normalizePath($route), $query, $headers, $body));
    $content = $response->content();
    $json = str_starts_with($response->contentType, 'application/json') && $content !== '' ? json_decode($content, true) : null;

    $problems = [];
    $expected = (array) $step['expect'];
    if (!in_array($response->status, $expected, true)) {
        $problems[] = 'expected status ' . implode(' or ', $expected) . ", got {$response->status}";
    }
    foreach ($step['expect_headers'] ?? [] as $name => $value) {
        if ($response->header($name) !== $value) {
            $problems[] = "header {$name}: expected {$value}, got " . ($response->header($name) ?? 'nothing');
        }
    }
    foreach ($step['equals'] ?? [] as $jsonPath => $expected) {
        $expected = $resolve($expected, $vars);
        $actual = $dig($json, $jsonPath);
        if ($actual !== $expected) {
            $problems[] = "{$jsonPath}: expected " . json_encode($expected) . ', got ' . ($actual === $missing ? 'nothing' : json_encode($actual));
        }
    }
    foreach ($step['absent'] ?? [] as $jsonPath) {
        if ($dig($json, $jsonPath) !== $missing) {
            $problems[] = "{$jsonPath} must not be present";
        }
    }

    if ($problems !== []) {
        fwrite(STDERR, "FAIL {$step['name']} ({$step['method']} {$path})" . PHP_EOL);
        foreach ($problems as $problem) {
            fwrite(STDERR, "  - {$problem}" . PHP_EOL);
        }
        fwrite(STDERR, '  response: ' . $content . PHP_EOL);
        exit(1);
    }

    foreach ($step['save'] ?? [] as $name => $jsonPath) {
        $vars[$name] = $dig($json, $jsonPath);
    }
    echo "PASS {$step['name']}" . PHP_EOL;
    $passed++;
}

echo PHP_EOL . "{$passed} scenario steps passed." . PHP_EOL;

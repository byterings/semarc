<?php

declare(strict_types=1);

// Replays tests/api_scenario.json against the application in-process,
// using a fresh in-memory SQLite database. Run: php tests/run.php

putenv('DB_CONNECTION=sqlite');
putenv('DB_DATABASE=:memory:');
putenv('BOOTSTRAP_ADMIN_EMAIL=admin@example.com');
putenv('MAIL_DRIVER=memory');
putenv('RATE_LIMIT_STORAGE=' . sys_get_temp_dir() . '/semarc-rate-limits-' . bin2hex(random_bytes(6)));
if (getenv('JWT_SECRET') === false) {
    putenv('JWT_SECRET=semarc-test-secret-semarc-test-secret');
}

$scenario = json_decode((string) file_get_contents(__DIR__ . '/api_scenario.json'), true, 512, JSON_THROW_ON_ERROR);
foreach ($scenario['env'] ?? [] as $name => $value) {
    putenv("{$name}={$value}");
}

require_once __DIR__ . '/../bootstrap.php';

(new Migrator(Database::connection(), __DIR__ . '/../migrations'))->run();
/** @var Router $router */
$router = require __DIR__ . '/../routes.php';

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
// Cookie sessions (AUTH SESSION): session cookie per saved credential variable.
$session = $scenario['session'] ?? null;
$sessionCookies = [];
$unsafe = static fn (string $method): bool => !in_array($method, ['GET', 'HEAD', 'OPTIONS'], true);
foreach ($scenario['steps'] as $step) {
    if (isset($step['external'])) {
        echo "SKIP {$step['name']} (needs an external service)" . PHP_EOL;
        continue;
    }
    if (isset($step['mail'])) {
        $mail = $step['mail'];
        $found = null;
        foreach (array_reverse(class_exists('Mailer') ? Mailer::$outbox : []) as $message) {
            if ($message['to'] === $mail['to'] && $message['subject'] === $mail['subject']) {
                $found = $message;
                break;
            }
        }
        if ($found === null || preg_match('/' . $mail['pattern'] . '/', $found['body'], $matches) !== 1) {
            fwrite(STDERR, "FAIL {$step['name']}: no email \"{$mail['subject']}\" to {$mail['to']} matching {$mail['pattern']}" . PHP_EOL);
            exit(1);
        }
        $vars[$mail['save']] = $matches[1];
        echo "PASS {$step['name']}" . PHP_EOL;
        $passed++;
        continue;
    }
    $path = preg_replace_callback('/\$\{(\w+)\}/', static fn (array $m): string => (string) ($vars[$m[1]] ?? ''), $step['path']);
    $headers = ['content-type' => 'application/json'];
    foreach ($step['headers'] ?? [] as $name => $value) {
        $headers[strtolower($name)] = $value;
    }
    $credential = null;
    if (!empty($step['auth'])) {
        $name = $step['auth_as'] ?? 'token';
        $credential = [(string) ($sessionCookies[$name] ?? ''), (string) ($vars[$name] ?? '')];
    }
    if (isset($step['token'])) {
        $credential = [$step['token'], $step['token']];
    }
    if ($credential !== null && $session === null) {
        $headers['authorization'] = 'Bearer ' . $credential[1];
    } elseif ($credential !== null) {
        $headers['cookie'] = $session['cookie'] . '=' . $credential[0];
        if ($unsafe($step['method']) && ($step['csrf'] ?? true)) {
            $headers[strtolower($session['csrf_header'])] = $credential[1];
        }
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

    $issued = null;
    foreach ($session === null ? [] : $response->cookies as $cookie) {
        if (str_starts_with($cookie, $session['cookie'] . '=')) {
            $attributes = strtolower($cookie);
            if (!str_contains($attributes, 'httponly') || !str_contains($attributes, 'samesite=lax')) {
                fwrite(STDERR, "FAIL {$step['name']}: session cookie must be HttpOnly and SameSite=Lax: {$cookie}" . PHP_EOL);
                exit(1);
            }
            $issued = rawurldecode(explode(';', substr($cookie, strlen($session['cookie']) + 1))[0]);
        }
    }
    foreach ($step['save'] ?? [] as $name => $jsonPath) {
        $vars[$name] = $dig($json, $jsonPath);
        if ($issued !== null && str_ends_with($jsonPath, 'csrf_token')) {
            $sessionCookies[$name] = $issued;
        }
    }
    echo "PASS {$step['name']}" . PHP_EOL;
    $passed++;
}

echo PHP_EOL . "{$passed} scenario steps passed." . PHP_EOL;

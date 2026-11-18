<?php

declare(strict_types=1);

$router = new Router();

$router->useAuthenticator(static function (Request $request): void {
    (new AuthMiddleware())->authenticate($request);
});

$project = [
    'project' => 'GoldenAPI',
    'target' => 'PHP',
    'semarc_version' => '0.14.0',
    'models' => ['User'],
    'routes' => ['GET /', 'GET /health', 'GET /routes', 'GET /openapi.json', 'GET /docs', 'POST /login', 'GET /users', 'POST /register', 'GET /me'],
];

$router->add('GET', '/', static fn (): Response => Response::html(HomePage::render($project)));
$router->add('GET', '/health', static function () use ($project): Response {
    try {
        Database::connection()->query('SELECT 1');
        $database = 'ok';
    } catch (Throwable $exception) {
        error_log((string) $exception);
        $database = 'unavailable';
    }

    return Response::json(
        ['status' => $database === 'ok' ? 'ok' : 'degraded', 'project' => $project['project'], 'database' => $database],
        $database === 'ok' ? 200 : 503,
    );
});
$router->add('GET', '/routes', static fn (): array => ['routes' => $router->routes()]);
$router->add('GET', '/openapi.json', static fn (): Response => Response::file((string) file_get_contents(__DIR__ . '/openapi.json'), 'application/json; charset=utf-8'));
$router->add('GET', '/docs', static fn (): Response => Response::file((string) file_get_contents(__DIR__ . '/docs.html'), 'text/html; charset=utf-8'));

$router->add('POST', '/login', static fn (Request $request): array => (new AuthController())->login($request));
$router->add('GET', '/users', static fn (Request $request): array => (new UserController())->list($request), true);
$router->add('POST', '/register', static fn (Request $request): Response => (new AuthController())->register($request));
$router->add('GET', '/me', static fn (Request $request): array => (new AuthController())->me($request), true);

return $router;

<?php

declare(strict_types=1);

final class Router
{
    /** @var list<array{method: string, path: string, pattern: string, handler: callable, protected: bool}> */
    private array $routes = [];

    /** @var (callable(Request): void)|null */
    private $authenticator = null;

    public function useAuthenticator(callable $authenticator): void
    {
        $this->authenticator = $authenticator;
    }

    public function add(string $method, string $path, callable $handler, bool $protected = false): void
    {
        $this->routes[] = [
            'method' => $method,
            'path' => $path,
            'pattern' => $this->compile($path),
            'handler' => $handler,
            'protected' => $protected,
        ];
    }

    /**
     * @return list<string>
     */
    public function routes(): array
    {
        return array_map(fn (array $route): string => $route['method'] . ' ' . $route['path'], $this->routes);
    }

    public function dispatch(Request $request): Response
    {
        if (Cors::isPreflight($request)) {
            return Cors::preflight($request);
        }

        return Cors::apply($request, $this->handle($request));
    }

    private function handle(Request $request): Response
    {
        try {
            $allowed = [];
            foreach ($this->routes as $route) {
                if (preg_match($route['pattern'], $request->path, $matches) !== 1) {
                    continue;
                }
                if ($route['method'] !== $request->method) {
                    $allowed[] = $route['method'];
                    continue;
                }

                if ($route['protected']) {
                    if ($this->authenticator === null) {
                        throw new RuntimeException('Protected route registered without an authenticator.');
                    }
                    ($this->authenticator)($request);
                }

                $params = array_filter($matches, 'is_string', ARRAY_FILTER_USE_KEY);
                $result = ($route['handler'])($request, $params);

                return $result instanceof Response ? $result : Response::json($result);
            }

            if ($allowed !== []) {
                throw new HttpException(405, 'method_not_allowed', 'Method not allowed. Allowed: ' . implode(', ', array_unique($allowed)) . '.');
            }

            throw HttpException::notFound('Route not found.');
        } catch (HttpException $exception) {
            return Response::error($exception);
        } catch (Throwable $exception) {
            error_log((string) $exception);

            return Response::error(new HttpException(500, 'internal_error', 'Internal server error.'));
        }
    }

    private function compile(string $path): string
    {
        $segments = array_map(
            static function (string $segment): string {
                if (preg_match('/^\{([a-z][a-z0-9_]*)\}$/', $segment, $matches) === 1) {
                    return '(?P<' . $matches[1] . '>[^/]+)';
                }

                return preg_quote($segment, '#');
            },
            explode('/', trim($path, '/')),
        );

        return '#^/' . implode('/', $segments) . '$#';
    }
}

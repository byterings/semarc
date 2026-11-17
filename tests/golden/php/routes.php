<?php

require_once __DIR__ . '/controllers/AuthController.php';
require_once __DIR__ . '/controllers/UserController.php';

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($method === 'GET' && $path === '/') {
    header('Content-Type: text/html; charset=utf-8');
    $project = ['project' => 'GoldenAPI', 'target' => 'PHP', 'semarc_version' => '0.13.0', 'models' => ['User'], 'routes' => ['GET /', 'GET /health', 'GET /routes', 'POST /login', 'GET /users', 'POST /register', 'GET /me'], 'profiles' => [], 'modules' => [], 'status' => 'Running'];
    echo '<h1>SEMARC Generated Project</h1>';
    echo '<p><strong>Project:</strong> ' . htmlspecialchars($project['project']) . '</p>';
    echo '<p><strong>Target:</strong> ' . htmlspecialchars($project['target']) . '</p>';
    echo '<p><strong>SEMARC Version:</strong> ' . htmlspecialchars($project['semarc_version']) . '</p>';
    echo '<h2>Models</h2><ul>';
    foreach ($project['models'] as $item) { echo '<li>' . htmlspecialchars($item) . '</li>'; }
    echo '</ul><h2>Routes</h2><ul>';
    foreach ($project['routes'] as $item) { echo '<li>' . htmlspecialchars($item) . '</li>'; }
    echo '</ul><p><strong>Status:</strong> ' . htmlspecialchars($project['status']) . '</p>';
    exit;
}

if ($method === 'GET' && $path === '/health') {
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok', 'project' => 'GoldenAPI']);
    exit;
}

if ($method === 'GET' && $path === '/routes') {
    header('Content-Type: application/json');
    echo json_encode(['routes' => ['GET /', 'GET /health', 'GET /routes', 'POST /login', 'GET /users', 'POST /register', 'GET /me']]);
    exit;
}

if ($method === 'POST' && $path === '/login') {
    $controller = new AuthController();
    $controller->login();
    exit;
}

if ($method === 'GET' && $path === '/users') {
    $controller = new UserController();
    $controller->index();
    exit;
}

if ($method === 'POST' && $path === '/register') {
    http_response_code(501);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Generated TODO: connect this route to a business service.']);
    exit;
}

if ($method === 'GET' && $path === '/me') {
    http_response_code(501);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Generated TODO: connect this route to a business service.']);
    exit;
}

http_response_code(404);
echo json_encode(['error' => 'Route not found']);

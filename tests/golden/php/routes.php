<?php

require_once __DIR__ . '/controllers/AuthController.php';

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($method === 'POST' && $path === '/login') {
    $controller = new AuthController();
    $controller->login();
    exit;
}

if ($method === 'GET' && $path === '/users') {
    header('Content-Type: application/json');
    echo json_encode(['data' => []]);
    exit;
}

http_response_code(404);
echo json_encode(['error' => 'Route not found']);

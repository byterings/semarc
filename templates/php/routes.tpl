<?php

{{requires}}

$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

{{route_blocks}}
http_response_code(404);
echo json_encode(['error' => 'Route not found']);

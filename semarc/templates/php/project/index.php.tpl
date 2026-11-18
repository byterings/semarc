<?php

declare(strict_types=1);

require_once __DIR__ . '/../bootstrap.php';

/** @var Router $router */
$router = require __DIR__ . '/../routes.php';
$router->dispatch(Request::capture())->send();

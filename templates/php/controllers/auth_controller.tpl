<?php

require_once __DIR__ . '/../validators/Validator.php';

class {{controller_name}}
{
    private Validator $validator;

    public function __construct()
    {
        $this->validator = new Validator();
    }

    public function login(): void
    {
        header('Content-Type: application/json');
        $input = json_decode(file_get_contents('php://input'), true) ?? [];

        $errors = $this->validator->validate($input, [
            'email' => ['required', 'email'],
            'password' => ['required', 'min:6'],
        ]);

        if ($errors !== []) {
            http_response_code(422);
            echo json_encode(['errors' => $errors]);
            return;
        }

        http_response_code(501);
        echo json_encode([
            'error' => 'Authentication implementation is a generated TODO scaffold.',
            'project' => '{{project_name}}',
        ]);
    }
}

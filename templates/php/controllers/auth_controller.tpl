<?php

require_once __DIR__ . '/../services/TokenService.php';
require_once __DIR__ . '/../services/PasswordHasher.php';
require_once __DIR__ . '/../validators/Validator.php';

class {{controller_name}}
{
    private TokenService $tokens;
    private PasswordHasher $passwords;
    private Validator $validator;

    public function __construct()
    {
        $this->tokens = new TokenService();
        $this->passwords = new PasswordHasher();
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

        $token = $this->tokens->generate([
            'email' => $input['email'],
            'project' => '{{project_name}}',
        ]);

        echo json_encode([
            'token' => $token,
            'project' => '{{project_name}}',
        ]);
    }
}

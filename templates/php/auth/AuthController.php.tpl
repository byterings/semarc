<?php

declare(strict_types=1);

final class AuthController
{
    private {{auth_model}}Service $users;
    private {{auth_model}}Repository $repository;
    private TokenService $tokens;
    private PasswordHasher $hasher;

    public function __construct()
    {
        $this->users = new {{auth_model}}Service();
        $this->repository = new {{auth_model}}Repository();
        $this->tokens = new TokenService();
        $this->hasher = new PasswordHasher();
    }

    public function register(Request $request): Response
    {
        $user = $this->users->create($request->json());

        return Response::json(['data' => ['user' => $user] + $this->tokens->issue($user['id'])], 201);
    }

    /**
     * @return array<string, mixed>
     */
    public function login(Request $request): array
    {
        $input = $request->json();
        $errors = [];
        foreach (['{{identity_field}}', '{{secret_field}}'] as $field) {
            if (!isset($input[$field]) || !is_string($input[$field]) || $input[$field] === '') {
                $errors[$field][] = "{$field} is required";
            }
        }
        if ($errors !== []) {
            throw HttpException::validation($errors);
        }

        $record = $this->repository->findBy('{{identity_field}}', $input['{{identity_field}}']);
        if ($record === null || !$this->hasher->verify($input['{{secret_field}}'], (string) $record['{{secret_field}}'])) {
            throw HttpException::unauthorized('Invalid credentials.');
        }

        return ['data' => $this->tokens->issue((int) $record['id'])];
    }

    /**
     * @return array<string, mixed>
     */
    public function me(Request $request): array
    {
        return ['data' => $this->users->get((int) $request->userId)];
    }
}

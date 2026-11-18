<?php

declare(strict_types=1);

final class AuthMiddleware
{
    private TokenService $tokens;
    private {{auth_model}}Repository $users;

    public function __construct()
    {
        $this->tokens = new TokenService();
        $this->users = new {{auth_model}}Repository();
    }

    public function authenticate(Request $request): void
    {
        $token = $request->bearerToken() ?? throw HttpException::unauthorized('Missing bearer token.');
        $userId = $this->tokens->userIdFrom($token);
        if ($this->users->findById($userId) === null) {
            throw HttpException::unauthorized('Token user no longer exists.');
        }

        $request->userId = $userId;
    }
}

<?php

declare(strict_types=1);

/** Authenticates the session cookie; unsafe methods also need the CSRF header. */
final class AuthMiddleware
{
    private const SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS'];

    private Sessions $sessions;
    private {{auth_model}}Repository $users;

    public function __construct()
    {
        $this->sessions = new Sessions();
        $this->users = new {{auth_model}}Repository();
    }

    public function authenticate(Request $request): void
    {
        $session = $this->sessions->find($request) ?? throw HttpException::unauthorized('Missing, ended or expired session.');
        if (!in_array($request->method, self::SAFE_METHODS, true)) {
            $csrf = $request->header(Sessions::CSRF_HEADER);
            if ($csrf === null || !hash_equals((string) $session['csrf_hash'], hash('sha256', $csrf))) {
                throw HttpException::forbidden('Missing or invalid CSRF token.');
            }
        }
        $userId = (int) $session['user_id'];
        $user = $this->users->findById($userId);
        if ($user === null) {
            throw HttpException::unauthorized('Session user no longer exists.');
        }

        $request->userId = $userId;
        $request->userRole = isset($user['role']) ? (string) $user['role'] : null;
    }
}

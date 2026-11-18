<?php

declare(strict_types=1);

final class AuthController
{
    private {{auth_model}}Service $users;
    private {{auth_model}}Repository $repository;
    private TokenService $tokens;
    private RefreshTokens $refreshTokens;
    private PasswordHasher $hasher;

    public function __construct()
    {
        $this->users = new {{auth_model}}Service();
        $this->repository = new {{auth_model}}Repository();
        $this->tokens = new TokenService();
        $this->refreshTokens = new RefreshTokens();
        $this->hasher = new PasswordHasher();
    }

    public function register(Request $request): Response
    {
        RateLimiter::forAuth()->hit('register|' . $request->ip);
        $user = $this->users->create($request->json());
{{register_extra}}
        return Response::json(['data' => ['user' => $user] + $this->session($user['id'])], 201);
    }

    /**
     * @return array<string, mixed>
     */
    public function login(Request $request): array
    {
        RateLimiter::forAuth()->hit('login|' . $request->ip);
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

        return ['data' => $this->session((int) $record['id'])];
    }

    /**
     * Exchanges a refresh token for new tokens; the old refresh token stops working.
     *
     * @return array<string, mixed>
     */
    public function refresh(Request $request): array
    {
        RateLimiter::forAuth()->hit('refresh|' . $request->ip);
        $userId = $this->refreshTokens->rotate(self::requiredString($request->json(), 'refresh_token'));
        if ($this->repository->findById($userId) === null) {
            throw HttpException::unauthorized('Token user no longer exists.');
        }

        return ['data' => $this->session($userId)];
    }

    public function logout(Request $request): Response
    {
        $this->refreshTokens->revoke(self::requiredString($request->json(), 'refresh_token'));

        return Response::noContent();
    }

    public function changePassword(Request $request): Response
    {
        $input = $request->json();
        $current = self::requiredString($input, 'current_password');
        $new = self::validatedPassword($input['new_password'] ?? null, 'new_password');

        $userId = (int) $request->userId;
        $record = $this->repository->findById($userId);
        if ($record === null || !$this->hasher->verify($current, (string) $record['{{secret_field}}'])) {
            throw HttpException::validation(['current_password' => ['current_password is incorrect']]);
        }
        $this->repository->update($userId, ['{{secret_field}}' => $this->hasher->hash($new)]);
        $this->refreshTokens->revokeAll($userId);

        return Response::noContent();
    }

    /**
     * @return array<string, mixed>
     */
    private function session(int $userId): array
    {
        return $this->tokens->issue($userId) + $this->refreshTokens->issue($userId);
    }

    /** Applies the {{secret_field}} field rules to a new password; errors use $label as the field name. */
    private static function validatedPassword(mixed $value, string $label): string
    {
        try {
            return (new Validator())->validate(
                ['{{secret_field}}' => $value],
                ['{{secret_field}}' => {{auth_model}}::FIELDS['{{secret_field}}']],
            )['{{secret_field}}'];
        } catch (HttpException $exception) {
            throw HttpException::validation([$label => str_replace('{{secret_field}}', $label, $exception->details['{{secret_field}}'] ?? [])]);
        }
    }
{{extra_methods}}
    /**
     * @param array<string, mixed> $input
     */
    private static function requiredString(array $input, string $field): string
    {
        if (!isset($input[$field]) || !is_string($input[$field]) || $input[$field] === '') {
            throw HttpException::validation([$field => ["{$field} is required"]]);
        }

        return $input[$field];
    }

    /**
     * @return array<string, mixed>
     */
    public function me(Request $request): array
    {
        return ['data' => $this->users->get((int) $request->userId)];
    }
}

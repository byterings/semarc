<?php

class {{class_name}}
{
    private array $users = [];

    public function createUser(array $data): array
    {
        $user = [
            'id' => count($this->users) + 1,
            'name' => $data['name'] ?? '',
            'email' => $data['email'] ?? '',
            'password' => $data['password'] ?? '',
        ];

        $this->users[] = $user;

        return $user;
    }

    public function findUserByEmail(string $email): ?array
    {
        foreach ($this->users as $user) {
            if (($user['email'] ?? '') === $email) {
                return $user;
            }
        }

        return null;
    }

    public function getUsers(): array
    {
        return $this->users;
    }
{{relationship_methods}}
}

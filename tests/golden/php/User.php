<?php

class User
{
    public string $email;
    public string $name;


    public function __construct(array $data = [])
    {
        $this->email = $data['email'] ?? '';
        $this->name = $data['name'] ?? '';
    }

}

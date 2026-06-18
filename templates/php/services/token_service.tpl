<?php

class {{class_name}}
{
    public function generate(array $payload): string
    {
        throw new RuntimeException('TODO: configure a real token provider for {{class_name}}.');
    }

    public function validate(string $token): ?array
    {
        throw new RuntimeException('TODO: configure a real token validator for {{class_name}}.');
    }
}

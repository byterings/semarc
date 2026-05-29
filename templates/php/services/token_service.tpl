<?php

class {{class_name}}
{
    private string $secretKey = '{{secret_key}}';

    public function generate(array $payload): string
    {
        $payload['issued_at'] = time();
        $json = json_encode($payload);

        return base64_encode($json . '.' . $this->secretKey);
    }

    public function validate(string $token): ?array
    {
        $decoded = base64_decode($token, true);

        if ($decoded === false || !str_ends_with($decoded, '.' . $this->secretKey)) {
            return null;
        }

        $json = substr($decoded, 0, -strlen('.' . $this->secretKey));
        $payload = json_decode($json, true);

        return is_array($payload) ? $payload : null;
    }
}

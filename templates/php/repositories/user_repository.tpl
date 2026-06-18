<?php

class {{class_name}}
{
    public function {{create_method}}(array $data): array
    {
        // TODO: connect this repository to the selected database adapter.
        return [
            'status' => 'TODO',
            'data' => $data,
        ];
    }

    public function {{find_method}}(int $id): ?array
    {
        // TODO: connect this repository to the selected database adapter.
        return null;
    }

    public function {{list_method}}(): array
    {
        // TODO: connect this repository to the selected database adapter.
        return [];
    }
{{relationship_methods}}
}

<?php

class {{class_name}}
{
    public function up(): string
    {
        return <<<'SQL'
{{sql}}
SQL;
    }
}

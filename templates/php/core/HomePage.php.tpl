<?php

declare(strict_types=1);

final class HomePage
{
    /**
     * @param array<string, mixed> $project
     */
    public static function render(array $project): string
    {
        $escape = static fn (string $value): string => htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
        $list = static fn (array $items): string => implode('', array_map(
            static fn (string $item): string => '<li>' . $escape($item) . '</li>',
            $items,
        ));

        return '<!doctype html><html><head><meta charset="utf-8"><title>' . $escape($project['project']) . '</title></head><body>'
            . '<h1>SEMARC Generated Project</h1>'
            . '<p><strong>Project:</strong> ' . $escape($project['project']) . '</p>'
            . '<p><strong>Target:</strong> ' . $escape($project['target']) . '</p>'
            . '<p><strong>SEMARC Version:</strong> ' . $escape($project['semarc_version']) . '</p>'
            . '<h2>Models</h2><ul>' . $list($project['models']) . '</ul>'
            . '<h2>Routes</h2><ul>' . $list($project['routes']) . '</ul>'
            . '<p><strong>Status:</strong> Running</p>'
            . '</body></html>';
    }
}

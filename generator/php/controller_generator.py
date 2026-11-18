from generator.php.base import PHP_HEADER, PhpFileWriter
from generator.utils.inflector import pascal_case
from generator.utils.resource_views import operation_kinds, related_parents

ITEM_KINDS = {"read", "update", "replace", "delete"}


class ControllerGenerator:
    """Maps IR API operations to PHP controller actions."""

    def __init__(self, writer: PhpFileWriter) -> None:
        self.writer = writer

    def generate(self, ir: dict) -> list[str]:
        files = []
        for model in ir["models"]:
            kinds = operation_kinds(ir, model["name"])
            if not kinds:
                continue
            path = f"controllers/{model['name']}Controller.php"
            self.writer.write(path, self._controller(ir, model, kinds), "php controller")
            files.append(path)
        return files

    def _controller(self, ir: dict, model: dict, kinds: list[str]) -> str:
        name = model["name"]
        methods = []
        if "list" in kinds:
            methods.append(self._method("list", "Request $request", "array", [
                "return $this->service->list(",
                "    $request->queryInt('limit', ResourceService::DEFAULT_LIMIT),",
                "    $request->queryInt('offset', 0),",
                "    $request->query,",
                ");",
            ]))
        if "read" in kinds:
            methods.append(self._method("read", "Request $request, string $id", "array", [
                "return ['data' => $this->service->get(self::id($id))];",
            ]))
        if "create" in kinds:
            methods.append(self._method("create", "Request $request", "Response", [
                "return Response::json(['data' => $this->service->create($request->json(), $request->userId)], 201);",
            ]))
        if "replace" in kinds:
            methods.append(self._method("replace", "Request $request, string $id", "array", [
                "return ['data' => $this->service->update(self::id($id), $request->json(), false, $request->userId)];",
            ]))
        if "update" in kinds:
            methods.append(self._method("update", "Request $request, string $id", "array", [
                "return ['data' => $this->service->update(self::id($id), $request->json(), true, $request->userId)];",
            ]))
        if "delete" in kinds:
            methods.append(self._method("delete", "Request $request, string $id", "Response", [
                "$this->service->delete(self::id($id), $request->userId);",
                "",
                "return Response::noContent();",
            ]))
        for parent in related_parents(ir, name):
            methods.append(self._method(f"listBy{pascal_case(parent['model'])}", "Request $request, string $parentId", "array", [
                "return $this->service->listForParent(",
                f"    '{parent['model']}',",
                f"    '{parent['table']}',",
                f"    '{parent['column']}',",
                "    self::id($parentId),",
                "    $request->queryInt('limit', ResourceService::DEFAULT_LIMIT),",
                "    $request->queryInt('offset', 0),",
                "    $request->query,",
                ");",
            ]))
        if ITEM_KINDS & set(kinds) or related_parents(ir, name):
            methods.append(
                "\n".join(
                    [
                        "    private static function id(string $value): int",
                        "    {",
                        "        if (preg_match('/^[1-9]\\d{0,17}$/', $value) !== 1) {",
                        f"            throw HttpException::notFound(\"Record {{$value}} not found.\");",
                        "        }",
                        "",
                        "        return (int) $value;",
                        "    }",
                    ]
                )
            )

        return "\n".join(
            [
                PHP_HEADER,
                f"final class {name}Controller",
                "{",
                f"    private {name}Service $service;",
                "",
                "    public function __construct()",
                "    {",
                f"        $this->service = new {name}Service();",
                "    }",
                "",
                "\n\n".join(methods),
                "}",
                "",
            ]
        )

    def _method(self, name: str, parameters: str, return_type: str, body: list[str]) -> str:
        lines = [f"    public function {name}({parameters}): {return_type}", "    {"]
        lines.extend(f"        {line}" if line else "" for line in body)
        lines.append("    }")
        return "\n".join(lines)

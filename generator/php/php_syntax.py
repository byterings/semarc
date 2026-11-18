def php_literal(value, indent: int = 0) -> str:
    """Renders a Python value as a deterministic PHP literal."""
    pad = " " * indent
    inner = " " * (indent + 4)
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, dict):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value.values()):
            return "[" + ", ".join(f"{php_literal(key)} => {php_literal(item)}" for key, item in value.items()) + "]"
        entries = [f"{inner}{php_literal(key)} => {php_literal(item, indent + 4)}," for key, item in value.items()]
        return "[\n" + "\n".join(entries) + f"\n{pad}]"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        if all(not isinstance(item, (dict, list)) for item in value):
            return "[" + ", ".join(php_literal(item) for item in value) + "]"
        entries = [f"{inner}{php_literal(item, indent + 4)}," for item in value]
        return "[\n" + "\n".join(entries) + f"\n{pad}]"
    raise TypeError(f"Unsupported PHP literal: {value!r}")

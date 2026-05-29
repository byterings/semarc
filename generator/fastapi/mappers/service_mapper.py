from generator.fastapi.mappers.name_utils import snake_case


class ServiceMapper:
    """Maps IR services and validators into FastAPI service modules."""

    def map(self, ir: dict) -> list[dict]:
        mapped = []

        for service in ir["services"]:
            template = {
                "TokenService": "services/token_service.tpl",
                "PasswordHasher": "services/password_hasher.tpl",
            }[service["name"]]
            mapped.append(
                {
                    "path": f"services/{snake_case(service['name'])}.py",
                    "template": template,
                    "values": {
                        "secret_key": f"{ir['project']}_prototype_secret",
                    },
                }
            )

        validator_names = sorted({validator["name"] for validator in ir["validators"]})
        for validator_name in validator_names:
            mapped.append(
                {
                    "path": f"services/{snake_case(validator_name)}.py",
                    "template": "service.tpl",
                    "values": {
                        "class_name": validator_name,
                        "methods": self._validator_methods(),
                    },
                }
            )

        return mapped

    def _validator_methods(self) -> str:
        return "\n".join(
            [
                "    def required(self, data: dict, field: str):",
                "        if field not in data or str(data[field]).strip() == \"\":",
                "            return f\"{field} is required\"",
                "        return None",
                "",
                "    def email(self, data: dict, field: str):",
                "        value = data.get(field)",
                "        if value is None or \"@\" in str(value):",
                "            return None",
                "        return f\"{field} must be a valid email address\"",
                "",
                "    def min_length(self, data: dict, field: str, length: int):",
                "        value = str(data.get(field, \"\"))",
                "        if len(value) >= length:",
                "            return None",
                "        return f\"{field} must be at least {length} characters\"",
                "",
                "    def validate(self, data: dict, rules: dict) -> dict:",
                "        errors = {}",
                "        for field, field_rules in rules.items():",
                "            for rule in field_rules:",
                "                error = self._apply_rule(data, field, rule)",
                "                if error is not None:",
                "                    errors.setdefault(field, []).append(error)",
                "        return errors",
                "",
                "    def _apply_rule(self, data: dict, field: str, rule: str):",
                "        if rule == \"required\":",
                "            return self.required(data, field)",
                "        if rule == \"email\":",
                "            return self.email(data, field)",
                "        if rule.startswith(\"min:\"):",
                "            return self.min_length(data, field, int(rule[4:]))",
                "        return None",
            ]
        )

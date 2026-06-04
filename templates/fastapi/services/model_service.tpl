from repositories.{{repository_module}} import {{repository_class}}


class {{class_name}}:
    def __init__(self):
        self.{{repository_variable}} = {{repository_class}}()

    def list(self) -> list:
        return self.{{repository_variable}}.{{list_method}}()

    def create(self, payload: dict) -> dict:
        return self.{{repository_variable}}.{{create_method}}(payload)

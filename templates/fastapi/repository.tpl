class {{class_name}}:
    def {{create_method}}(self, data: dict) -> dict:
        # TODO: connect this repository to the selected database adapter.
        return {
            "status": "TODO",
            "data": data,
        }

    def find_by_id(self, record_id: int):
        # TODO: connect this repository to the selected database adapter.
        return None

    def {{list_method}}(self) -> list:
        # TODO: connect this repository to the selected database adapter.
        return []
{{relationship_methods}}

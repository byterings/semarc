class {{class_name}}:
    def __init__(self):
        self.{{collection_name}} = []

    def {{create_method}}(self, data: dict) -> dict:
        record = {
            "id": len(self.{{collection_name}}) + 1,
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "password": data.get("password", ""),
        }
        self.{{collection_name}}.append(record)
        return record

    def find_by_email(self, email: str):
        for record in self.{{collection_name}}:
            if record.get("email") == email:
                return record
        return None

    def {{list_method}}(self) -> list:
        return self.{{collection_name}}
{{relationship_methods}}

import base64
import json
import time


class TokenService:
    def __init__(self):
        self.secret_key = "{{secret_key}}"

    def generate(self, payload: dict) -> str:
        payload = dict(payload)
        payload["issued_at"] = int(time.time())
        raw = json.dumps(payload) + "." + self.secret_key
        return base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    def validate(self, token: str):
        try:
            decoded = base64.b64decode(token.encode("utf-8")).decode("utf-8")
        except Exception:
            return None

        suffix = "." + self.secret_key
        if not decoded.endswith(suffix):
            return None

        raw_payload = decoded[: -len(suffix)]
        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError:
            return None

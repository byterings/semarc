import bcrypt

BCRYPT_MAX_BYTES = 72


class PasswordHasher:
    def hash(self, plain: str) -> str:
        return bcrypt.hashpw(plain.encode()[:BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode()

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(plain.encode()[:BCRYPT_MAX_BYTES], hashed.encode())
        except ValueError:
            return False

from pwdlib import PasswordHash

_password_hasher = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _password_hasher.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)

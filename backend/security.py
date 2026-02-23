import os
from cryptography.fernet import Fernet

# key = Fernet.generate_key() 
# print(key.decode())

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_password(password: str) -> str:
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(token: str) -> str:
    return cipher_suite.decrypt(token.encode()).decode()
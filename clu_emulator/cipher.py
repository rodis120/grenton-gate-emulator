from base64 import b64decode

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class CluCipher:

    def __init__(self, key: str | bytes, iv: str | bytes) -> None:
        self._key = None
        self._iv = None
        self._cipher = None
        
        self.set_key(key, iv)    
        
        self._padding = padding.PKCS7(128)
        
    def set_key(self, key: str | bytes, iv: str | bytes) -> None:
        if isinstance(key, str):
            self._key = b64decode(key)
        else:
            self._key = key
            
        if isinstance(iv, str):
            self._iv = b64decode(iv)
        else:
            self._iv = iv
            
        self._cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(self._iv), backend=default_backend()
        )

    def encrypt(self, data: bytes) -> bytes:
        encryptor = self._cipher.encryptor()
        padder = self._padding.padder()
        data = padder.update(data) + padder.finalize()
        return encryptor.update(data) + encryptor.finalize()

    def decrypt(self, data: bytes) -> bytes:
        decryptor = self._cipher.decryptor()
        unpadder = self._padding.unpadder()
        data = decryptor.update(data) + decryptor.finalize()
        return unpadder.update(data) + unpadder.finalize()

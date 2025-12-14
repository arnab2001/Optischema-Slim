"""
Encryption service for sensitive data.
Uses Fernet symmetric encryption with environment-based key.
"""

import os
import base64
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    """Encrypt and decrypt sensitive data."""
    
    def __init__(self):
        # Get encryption key from environment
        encryption_key = os.getenv('ENCRYPTION_KEY')
        
        if not encryption_key:
            # Generate a key if not provided (dev only!)
            logger.warning("No ENCRYPTION_KEY found, generating temporary key")
            logger.warning("⚠️  Set ENCRYPTION_KEY in production! Generated key is not logged for security.")
            encryption_key = Fernet.generate_key().decode()
        
        # Ensure key is bytes
        if isinstance(encryption_key, str):
            encryption_key = encryption_key.encode()
        
        # Create cipher
        try:
            self.cipher = Fernet(encryption_key)
            logger.info("✅ Encryption service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_dict(self, data: dict, keys_to_encrypt: list) -> dict:
        """
        Encrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary with data
            keys_to_encrypt: List of keys to encrypt
            
        Returns:
            Dictionary with encrypted values
        """
        encrypted_data = data.copy()
        
        for key in keys_to_encrypt:
            if key in encrypted_data and encrypted_data[key]:
                encrypted_data[key] = self.encrypt(str(encrypted_data[key]))
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict, keys_to_decrypt: list) -> dict:
        """
        Decrypt specific keys in a dictionary.
        
        Args:
            data: Dictionary with encrypted data
            keys_to_decrypt: List of keys to decrypt
            
        Returns:
            Dictionary with decrypted values
        """
        decrypted_data = data.copy()
        
        for key in keys_to_decrypt:
            if key in decrypted_data and decrypted_data[key]:
                decrypted_data[key] = self.decrypt(str(decrypted_data[key]))
        
        return decrypted_data

# Global instance
encryption_service = EncryptionService()

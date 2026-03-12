"""
AES-256-GCM encryption/decryption for sensitive documents.
Encrypts Aadhaar and PAN files before storing in the database.
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 256-bit encryption key (32 bytes).
# In production, load from environment variable or secrets manager.
# For hackathon: stored here for demo purposes.
_KEY_ENV = os.environ.get("CIVICASSIST_ENCRYPTION_KEY")

if _KEY_ENV:
    ENCRYPTION_KEY = base64.b64decode(_KEY_ENV)
else:
    # Generate a stable key from a passphrase (deterministic for the project)
    # In production, use a properly managed key vault
    ENCRYPTION_KEY = b"CivicAssist2024SecureKey!@#$%^&*"  # Exactly 32 bytes


def encrypt_document(plaintext_bytes: bytes) -> dict:
    """
    Encrypt document bytes using AES-256-GCM.

    Returns:
        dict with 'nonce' (base64) and 'ciphertext' (bytes)
        The nonce is needed for decryption and must be stored alongside.
    """
    # Generate a random 96-bit nonce (12 bytes) for each encryption
    nonce = os.urandom(12)
    aesgcm = AESGCM(ENCRYPTION_KEY)

    # Encrypt with authentication (GCM provides both confidentiality + integrity)
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)

    return {
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": ciphertext,
    }


def decrypt_document(ciphertext: bytes, nonce_b64: str) -> bytes:
    """
    Decrypt document bytes using AES-256-GCM.

    Args:
        ciphertext: The encrypted bytes
        nonce_b64: Base64-encoded nonce used during encryption

    Returns:
        Original plaintext bytes
    """
    nonce = base64.b64decode(nonce_b64)
    aesgcm = AESGCM(ENCRYPTION_KEY)

    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext

"""Encryption utilities for secure storage of credentials using PostgreSQL's pgcrypto extension."""

from data_manipulation.encryption import decrypt_credentials, encrypt_credentials
from sqlalchemy.engine import Connection

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger()


def encrypt_basic_auth(
    connection: Connection, username: str, password: str
) -> str:
    """Encrypt username and password using PostgreSQL's pgp_sym_encrypt.

    Args:
        connection: SQLAlchemy database connection
        username: HTTP Basic Auth username
        password: HTTP Basic Auth password

    Returns:
        Encrypted string containing 'username:password' format

    Raises:
        Exception: If encryption fails
    """
    encryption_key = get_settings().ENCRYPTION_KEY

    try:
        return encrypt_credentials(connection, username, password, encryption_key)
    except Exception as e:
        logger.error(f"Failed to encrypt credentials: {e}")
        raise


def decrypt_basic_auth(
    connection: Connection, encrypted: str
) -> tuple[str, str]:
    """Decrypt username and password using PostgreSQL's pgp_sym_decrypt.

    Args:
        connection: SQLAlchemy database connection
        encrypted: Base64-encoded encrypted string

    Returns:
        Tuple of (username, password)

    Raises:
        ValueError: If decryption fails or format is invalid
        Exception: If database operation fails
    """
    encryption_key = get_settings().ENCRYPTION_KEY

    try:
        return decrypt_credentials(connection, encrypted, encryption_key)
    except Exception as e:
        logger.error(f"Failed to decrypt credentials: {e}")
        raise

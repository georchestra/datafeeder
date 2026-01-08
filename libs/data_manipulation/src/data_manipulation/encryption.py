"""Encryption utilities for secure storage of credentials using PostgreSQL's pgcrypto extension."""

from sqlalchemy import text
from sqlalchemy.engine import Connection


def encrypt_credentials(
    connection: Connection, username: str, password: str, encryption_key: str
) -> str:
    """Encrypt username and password using PostgreSQL's pgp_sym_encrypt.

    Args:
        connection: SQLAlchemy database connection
        username: HTTP Basic Auth username
        password: HTTP Basic Auth password
        encryption_key: Encryption key to use

    Returns:
        Base64-encoded encrypted string containing 'username:password' format

    Raises:
        ValueError: If encryption fails
        Exception: If database operation fails
    """
    credentials = f"{username}:{password}"

    try:
        result = connection.execute(
            text(
                "SELECT encode(pgp_sym_encrypt(:credentials, :key), 'base64') AS encrypted"
            ),
            {"credentials": credentials, "key": encryption_key},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError("Encryption returned no result")
        return row[0]
    except Exception as e:
        raise Exception(f"Failed to encrypt credentials: {e}") from e


def decrypt_credentials(
    connection: Connection, encrypted: str, encryption_key: str
) -> tuple[str, str]:
    """Decrypt username and password using PostgreSQL's pgp_sym_decrypt.

    Args:
        connection: SQLAlchemy database connection
        encrypted: Base64-encoded encrypted string
        encryption_key: Encryption key to use

    Returns:
        Tuple of (username, password)

    Raises:
        ValueError: If decryption fails or format is invalid
        Exception: If database operation fails
    """
    try:
        result = connection.execute(
            text(
                "SELECT pgp_sym_decrypt(decode(:encrypted, 'base64'), :key) AS decrypted"
            ),
            {"encrypted": encrypted, "key": encryption_key},
        )
        row = result.fetchone()
        if row is None:
            raise ValueError("Decryption returned no result")

        decrypted = row[0]
        if not isinstance(decrypted, (str, bytes)):
            raise ValueError(f"Unexpected decrypted type: {type(decrypted)}")

        # Convert bytes to string if necessary
        if isinstance(decrypted, bytes):
            decrypted = decrypted.decode("utf-8")

        # Parse 'username:password' format
        parts = decrypted.split(":", 1)
        if len(parts) != 2:
            raise ValueError("Decrypted credentials not in 'username:password' format")

        username, password = parts
        return username, password

    except Exception as e:
        raise Exception(f"Failed to decrypt credentials: {e}") from e

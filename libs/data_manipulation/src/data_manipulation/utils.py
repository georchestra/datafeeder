"""Utility functions for data manipulation."""

import logging
import re

import requests

from data_manipulation.logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger)


def sanitize_name(name: str) -> str:
    """
    Sanitize a name for use in GeoServer workspace/layer names or database schema names.

    Removes or replaces special characters:
    - Replaces spaces with underscores
    - Removes any character that is not alphanumeric, underscore, or hyphen
    - Converts to lowercase for consistency
    - Removes leading/trailing underscores or hyphens
    - Ensures the name doesn't start with a number (prefixes with 'layer_' if it does)

    Args:
        name: The name to sanitize

    Returns:
        str: The sanitized name

    Examples:
        >>> sanitize_name("My Organization Name")
        'my_organization_name'
        >>> sanitize_name("Org@123 #Test!")
        'org123_test'
        >>> sanitize_name("test--layer__name")
        'test_layer_name'
        >>> sanitize_name("123_dataset")
        'layer_123_dataset'
        >>> sanitize_name("_MyOrg_")
        'myorg'
    """
    import unicodedata

    # Normalize and remove accents
    sanitized = unicodedata.normalize("NFKD", name)
    sanitized = "".join(c for c in sanitized if not unicodedata.combining(c))
    # Replace spaces & hyphens with underscores
    sanitized = sanitized.replace(" ", "_")
    # Replace hyphens with underscores
    sanitized = sanitized.replace("-", "_")
    # Keep only alphanumeric characters, underscores, and hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "", sanitized)

    # Convert to lowercase
    sanitized = sanitized.lower()

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Ensure name doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"layer_{sanitized}"

    return sanitized[:63]


def resolve_url(url: str) -> str:
    """
    Check if a URL is 3xx redirection. If so, return location.

    Args:
        url: The URL to check
    Returns:
        str: The final URL after redirection or the original URL if no redirection
    """
    try:
        response = requests.head(url, allow_redirects=False, timeout=10)
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location")
            logger.info("URL %s redirected to %s", url, location)
            if location:
                return location
        return url
    except requests.RequestException as e:
        raise ValueError(f"Error checking URL {url}: {e}") from e

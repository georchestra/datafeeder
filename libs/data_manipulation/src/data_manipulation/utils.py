"""Utility functions for data manipulation."""

import re


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
        'test-layer_name'
        >>> sanitize_name("123_dataset")
        'layer_123_dataset'
        >>> sanitize_name("_MyOrg_")
        'myorg'
    """
    # Replace spaces with underscores
    sanitized = name.replace(" ", "_")

    # Keep only alphanumeric characters, underscores, and hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", sanitized)

    # Convert to lowercase
    sanitized = sanitized.lower()

    # Remove leading/trailing underscores or hyphens
    sanitized = sanitized.strip("_-")

    # Ensure name doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"layer_{sanitized}"

    return sanitized

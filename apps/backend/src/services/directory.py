"""Factory of the directory service (see :mod:`src.services.directory_service`)."""

from src.core.config import get_settings
from src.services.console_service import ConsoleService
from src.services.directory_service import DirectoryService
from src.services.keycloak_directory_service import KeycloakDirectoryService


def get_directory_service() -> DirectoryService:
    """Directory service selected by the ``DIRECTORY_PROVIDER`` setting."""
    settings = get_settings()
    if settings.DIRECTORY_PROVIDER == "keycloak":
        return KeycloakDirectoryService.from_settings(settings)
    return ConsoleService(settings.CONSOLE_INTERNAL_URL)

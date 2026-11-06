"""Directory of geOrchestra users, organizations and roles.

The backend needs a directory to list organizations/roles (group pickers), resolve their
identifiers (``IntegrityLinkRule.group_or_role``) and display names. Two implementations:

- ``console`` (default): the geOrchestra console internal API (``ConsoleService``)
- ``keycloak``: the Keycloak admin REST API (``KeycloakDirectoryService``), organizations
  being Keycloak groups and roles being realm roles

Select it with the ``DIRECTORY_PROVIDER`` setting and always obtain an instance through
:func:`src.services.directory.get_directory_service`.

All implementations return console-shaped dicts:

- organization: ``{"id", "shortName", "name", "mail"}``
- role: ``{"id", "name", "description"}``
"""

from typing import Any, Protocol


class DirectoryServiceError(Exception):
    """Raised when the directory is unreachable or returns an error."""


class DirectoryService(Protocol):
    def get_organization(self, org_short_name: str) -> dict[str, Any] | None:
        """Organization with this short name, None if not found or on error."""
        ...

    def get_all_organizations(self) -> list[dict[str, Any]]:
        """All organizations. Raises on error."""
        ...

    def get_all_roles(self) -> list[dict[str, Any]]:
        """All roles. Raises DirectoryServiceError on error."""
        ...

    def fetch_users_by_usernames(self, usernames: list[str]) -> dict[str, str]:
        """username -> "Firstname Lastname", {} on error."""
        ...

    def fetch_organizations_by_short_names(self, short_names: list[str]) -> dict[str, str]:
        """short name -> long name, {} on error."""
        ...

    def get_all_groups(self) -> list[dict[str, Any]]:
        """Groups metadata can be shared with (organization-shaped dicts): the organizations,
        and the other groups when the directory has some. Raises on error."""
        ...

    def get_user_groups(self, username: str) -> list[dict[str, Any]]:
        """Groups of a user (organization-shaped dicts), organization included; [] when the
        directory does not know them (the user's organization then applies) or on error."""
        ...

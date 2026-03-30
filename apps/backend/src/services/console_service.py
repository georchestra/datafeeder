from typing import Any

import httpx

from src.core.logging import get_logger

logger = get_logger()


class ConsoleService:
    """Service to interact with GeOrchestra Console API."""

    def __init__(self, console_url: str):
        """Initialize with GeoNetwork console API client.

        Args:
            console_url: GeoNetwork console API URL (e.g., http://geonetwork:8080/geonetwork/srv/console)
        """
        self.console_url = console_url

    def get_role_labels(self, role_ids: list[str]) -> list[str]:
        """Resolve role IDs to GeoServer-compatible role labels (ROLE_xxx format).

        Fetches all roles from the console API and returns the names matching the given IDs,
        prefixed with "ROLE_" as expected by GeoServer ACL.

        Args:
            role_ids: List of role IDs stored in IntegrityLinkRule.group_or_role.

        Returns:
            List of role labels in "ROLE_<name>" format. IDs with no matching role are skipped.
        """
        try:
            url = f"{self.console_url}/internal/roles"
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            all_roles: list[dict[str, Any]] = response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch roles from console API: {e}", exc_info=True)
            return []

        id_to_name = {
            str(r["id"]): str(r["name"]) for r in all_roles if r.get("id") and r.get("name")
        }
        return [f"ROLE_{id_to_name[rid]}" for rid in role_ids if rid in id_to_name]

    def get_organization(self, org_short_name: str) -> dict[str, Any] | None:
        """Fetch organization from geOrchestra console API.

        Args:
            org_short_name: Organization short name to match

        Returns:
            Organization dict if found, None otherwise
        """
        try:
            url = f"{self.console_url}/internal/organizations/shortname/{org_short_name}"
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()

            organization: dict[str, Any] = response.json()
            logger.info(f"Found organization for '{org_short_name}': {organization.get('name')}")
            return organization

        except Exception as e:
            logger.warning(
                f"Failed to fetch organization from console API: {e}",
                exc_info=True,
            )
            return None

    def get_all_organizations(self) -> list[dict[str, Any]]:
        """Fetch all organizations from geOrchestra console API.

        Returns:
            List of organization dicts.

        Raises:
            httpx.HTTPError: On network or HTTP errors.
            ValueError: If the response body is not valid JSON.
        """
        url = f"{self.console_url}/internal/organizations"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exc:
            logger.error("Console returned invalid JSON from %s", url)
            raise ValueError(f"Console returned invalid JSON from {url}") from exc

    def get_all_roles(self) -> list[dict[str, Any]]:
        """Fetch all roles from geOrchestra console API.

        Returns:
            List of role dicts.

        Raises:
            httpx.HTTPError: On network or HTTP errors.
            ValueError: If the response body is not valid JSON.
        """
        url = f"{self.console_url}/internal/roles"
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exc:
            logger.error("Console returned invalid JSON from %s", url)
            raise ValueError(f"Console returned invalid JSON from {url}") from exc

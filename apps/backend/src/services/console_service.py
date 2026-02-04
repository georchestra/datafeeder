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

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

    def get_organization_email(self, org_short_name: str) -> str | None:
        """Fetch organization email from geOrchestra console API.

        Args:
            org_short_name: Organization short name to match

        Returns:
            Organization email if found and defined, None otherwise
        """
        try:
            # Query console API for organizations
            url = f"{self.console_url}/internal/organizations"
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()

            organizations: list[dict[str, Any]] = response.json()

            # Find organization matching the short name
            for org in organizations:
                if org.get("shortName") == org_short_name:
                    org_email = org.get("mail")
                    if org_email:  # Only return if email is defined
                        logger.info(f"Found organization email for '{org_short_name}': {org_email}")
                        return str(org_email)
                    logger.warning(f"Organization '{org_short_name}' found but email not defined")
                    return None

            logger.warning(f"Organization '{org_short_name}' not found in console API")
            return None

        except Exception as e:
            logger.warning(
                f"Failed to fetch organization email from console API: {e}",
                exc_info=True,
            )
            return None

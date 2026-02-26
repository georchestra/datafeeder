import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger()


class GroupItem(BaseModel):
    id: str
    label: str


def fetch_groups(
    url: str,
    id_field: str,
    label_field: str,
    username: str = "",
    password: str = "",
) -> list[GroupItem]:
    """Fetch groups from an upstream JSON API and map to GroupItem list."""
    auth = None
    if username:
        auth = (username, password)

    try:
        response = httpx.get(url, auth=auth, timeout=10.0)
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.error(f"Failed to fetch groups from {url}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch groups from upstream: {e}")

    if response.status_code != 200:
        logger.error(f"Upstream returned {response.status_code} from {url}")
        raise HTTPException(
            status_code=502,
            detail=f"Upstream returned status {response.status_code}",
        )

    items = response.json()
    return [
        GroupItem(id=str(item[id_field]), label=str(item[label_field]))
        for item in items
        if id_field in item and label_field in item
    ]


def resolve_org_id(short_name: str) -> str | None:
    """Resolve an org shortName (sec-org header value) to its console UUID.

    The geOrchestra gateway injects the LDAP ``cn`` (e.g. ``PSC``) as
    ``sec-org``, while rules are stored with the console UUID as identifier.
    Fetches the organizations list on every call so that newly added or removed
    orgs are always reflected.

    Returns ``None`` if the org is not found or if the upstream call failed.
    In that case the caller should treat the user as having no org-based access.
    """
    settings = get_settings()
    try:
        items = fetch_groups(
            url=settings.METADATA_FETCH_GROUPS_URL,
            id_field="id",
            label_field="shortName",
            username=settings.METADATA_FETCH_GROUPS_USERNAME,
            password=settings.METADATA_FETCH_GROUPS_PASSWORD,
        )
        return {item.label: item.id for item in items}.get(short_name)
    except Exception:
        logger.warning(f"Could not resolve org '{short_name}' to UUID; treating as no org access")
        return None

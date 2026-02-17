import httpx
from fastapi import HTTPException
from pydantic import BaseModel

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

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import GeorchestraContextDep
from src.core.config import get_settings
from src.core.logging import get_logger

router = APIRouter(prefix="/metadata/groups", tags=["Metadata"])
logger = get_logger()


class GroupItem(BaseModel):
    id: str
    label: str


@router.get(
    "/",
    response_model=list[GroupItem],
    summary="List metadata groups",
    description="Fetch groups from the configured source and return identifier + label pairs.",
)
def list_groups(geo_ctx: GeorchestraContextDep) -> list[GroupItem]:
    settings = get_settings()
    url = settings.METADATA_FETCH_GROUPS_URL
    id_field = settings.METADATA_GROUPS_IDENTIFIER
    label_field = settings.METADATA_GROUPS_LABEL

    auth = None
    if settings.METADATA_FETCH_GROUPS_USERNAME:
        auth = (settings.METADATA_FETCH_GROUPS_USERNAME, settings.METADATA_FETCH_GROUPS_PASSWORD)

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
    result = []
    for item in items:
        if id_field in item and label_field in item:
            result.append(GroupItem(id=str(item[id_field]), label=str(item[label_field])))

    return result

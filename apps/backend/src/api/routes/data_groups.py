from fastapi import APIRouter, HTTPException

from src.api.deps import GeorchestraContextDep
from src.api.routes.groups_common import GroupItem, filter_console_items
from src.core.config import get_settings
from src.core.logging import get_logger
from src.services.directory import get_directory_service

logger = get_logger()

router = APIRouter(prefix="/data/groups", tags=["Data"])


@router.get(
    "/",
    response_model=list[GroupItem],
    summary="List data groups",
    description=(
        "Fetch the roles data rules can target from the directory (geOrchestra console roles, "
        "or one role per Keycloak group) and return identifier + label pairs."
    ),
)
def list_groups(geo_ctx: GeorchestraContextDep) -> list[GroupItem]:
    settings = get_settings()
    directory = get_directory_service()

    try:
        items = directory.get_data_roles()
    except Exception as e:
        logger.error("Failed to fetch data groups from directory: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch groups from directory: {e}")

    return [
        GroupItem(id=item["id"], label=str(item["description"] or item["name"]))
        for item in filter_console_items(items, settings.DATA_GROUPS_LABEL_FILTER_REGEX)
        if item.get("id") and item.get("name")
    ]

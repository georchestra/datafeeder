import re

from fastapi import APIRouter, HTTPException

from src.api.deps import GeorchestraContextDep
from src.api.routes.groups_common import GroupItem
from src.core.config import get_settings
from src.core.logging import get_logger
from src.services.console_service import ConsoleService

logger = get_logger()

router = APIRouter(prefix="/metadata/groups", tags=["Metadata"])


@router.get(
    "/",
    response_model=list[GroupItem],
    summary="List metadata groups",
    description=(
        "Fetch groups from geOrchestra console and return identifier + label pairs. "
        "Returns organizations when GN_SYNC_MODE=ORG, roles when GN_SYNC_MODE=ROLE."
    ),
)
def list_groups(geo_ctx: GeorchestraContextDep) -> list[GroupItem]:
    settings = get_settings()
    console_service = ConsoleService(settings.CONSOLE_URL)

    try:
        if settings.GN_SYNC_MODE == "ORG":
            items = console_service.get_all_organizations()
            group_items = [
                GroupItem(id=item["id"], label=item["name"])
                for item in items
                if item.get("id") and item.get("name")
            ]
        else:
            items = console_service.get_all_roles()
            group_items = [
                GroupItem(id=item["id"], label=item["name"])
                for item in items
                if item.get("id") and item.get("name")
            ]
    except Exception as e:
        logger.error("Failed to fetch metadata groups from console: %s", e)
        raise HTTPException(status_code=502, detail=f"Failed to fetch groups from console: {e}")

    if not settings.METADATA_GROUPS_LABEL_FILTER_REGEX:
        return group_items

    try:
        pattern = re.compile(settings.METADATA_GROUPS_LABEL_FILTER_REGEX)
    except re.error as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid METADATA_GROUPS_LABEL_FILTER_REGEX: {e}"
        )

    result: list[GroupItem] = []
    for item in group_items:
        match = pattern.search(item.label)
        if not match:
            continue

        new_label = match.group(1) if match.lastindex else match.group(0)
        result.append(GroupItem(id=item.id, label=new_label))

    return result

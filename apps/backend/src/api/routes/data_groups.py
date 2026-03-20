from fastapi import APIRouter

from src.api.deps import GeorchestraContextDep
from src.api.routes.groups_common import GroupItem, fetch_groups
from src.core.config import get_settings

router = APIRouter(prefix="/data/groups", tags=["Data"])


@router.get(
    "/",
    response_model=list[GroupItem],
    summary="List data groups",
    description="Fetch data groups from the configured source and return identifier + label pairs.",
)
def list_groups(geo_ctx: GeorchestraContextDep) -> list[GroupItem]:
    settings = get_settings()
    return fetch_groups(
        url=settings.DATA_FETCH_GROUPS_URL,
        id_field=settings.DATA_GROUPS_IDENTIFIER,
        label_field=settings.DATA_GROUPS_LABEL,
        username=settings.DATA_FETCH_GROUPS_USERNAME,
        password=settings.DATA_FETCH_GROUPS_PASSWORD,
        filter_regex=settings.DATA_GROUPS_LABEL_FILTER_REGEX,
    )

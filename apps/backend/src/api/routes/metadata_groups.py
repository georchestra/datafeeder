from fastapi import APIRouter

from src.api.deps import GeorchestraContextDep
from src.api.routes.groups_common import GroupItem, fetch_groups
from src.core.config import get_settings

router = APIRouter(prefix="/metadata/groups", tags=["Metadata"])


@router.get(
    "/",
    response_model=list[GroupItem],
    summary="List metadata groups",
    description="Fetch groups from the configured source and return identifier + label pairs.",
)
def list_groups(geo_ctx: GeorchestraContextDep) -> list[GroupItem]:
    settings = get_settings()
    return fetch_groups(
        url=settings.METADATA_FETCH_GROUPS_URL,
        id_field=settings.METADATA_GROUPS_IDENTIFIER,
        label_field=settings.METADATA_GROUPS_LABEL,
        username=settings.METADATA_FETCH_GROUPS_USERNAME,
        password=settings.METADATA_FETCH_GROUPS_PASSWORD,
        filter_regex=settings.METADATA_GROUPS_LABEL_FILTER_REGEX,
    )

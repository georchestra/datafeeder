from fastapi import APIRouter
from pydantic import BaseModel

from src.services.settings_service import get_settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


class ProjectionSetting(BaseModel):
    """Model for a projection setting."""

    value: str
    label: str


class SettingsResponse(BaseModel):
    """Response model for settings endpoint.

    Returns application settings including available projections.
    """

    projections: list[ProjectionSetting]
    enabled_features: list[str] = []


@router.get("/", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Get application settings.

    Returns:
        Application settings including projections
    """
    settings_service = get_settings_service()
    all_settings = settings_service.get_all_settings()
    return SettingsResponse(
        projections=all_settings.get("projections", []),
        enabled_features=all_settings.get("enabled_features", []),
    )

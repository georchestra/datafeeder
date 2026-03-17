from fastapi import APIRouter

from src.models.recurrence import (
    RecurrencePreset,
    RecurrencePresetItem,
)

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])


@router.get(
    "/recurrence-presets",
    response_model=list[RecurrencePresetItem],
    summary="List recurrence presets",
    description="Return the hardcoded list of recurrence presets with their cron expressions.",
)
def list_recurrence_presets() -> list[RecurrencePresetItem]:
    return [RecurrencePresetItem(id=preset, cron=preset.cron) for preset in RecurrencePreset]

"""Recurrence-schedule lifecycle of a dataset."""

from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import remove_ingestion_dag

__all__ = ["clear_schedule"]


def clear_schedule(integrity_link: IntegrityLink) -> bool:
    """Clear the recurrence schedule of a dataset.

    Single choke point pairing the field reset with the removal of the
    now-stale dynamic ingestion DAG (best-effort). The caller owns the
    session commit; removing the DAG before the commit is safe because the
    DAG generator re-emits it from the still-committed schedule if the
    commit later fails.

    Returns:
        True if a schedule was set and its ingestion DAG removal attempted.
    """
    had_schedule = bool(integrity_link.schedule)
    if had_schedule:
        remove_ingestion_dag(str(integrity_link.id))
    integrity_link.schedule = None
    integrity_link.schedule_enabled = False
    return had_schedule

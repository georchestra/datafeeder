"""Callback routes for Airflow DAG completion events."""

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callbacks", tags=["callbacks"])


@router.post("/staging/success")
async def staging_success_callback(
    dag_run_id: str = Query(..., description="DAG run ID"),
    staging_table_name: str = Query(..., description="Name of the staging table"),
) -> None:
    """Callback when staging_dag completes successfully.

    Args:
        dag_run_id: Unique identifier for the DAG run
        staging_table_name: Name of the staging table that was created

    Returns:
        JSON response with status
    """

    logger.info(
        f"Staging DAG succeeded - dag_run_id={dag_run_id}, staging_table={staging_table_name}"
    )

    # TODO: Cleanup staging table after configurable retention period


@router.post("/staging/failure")
async def staging_failure_callback(
    dag_run_id: str = Query(..., description="DAG run ID"),
) -> None:
    """Callback when staging_dag fails.

    Args:
        dag_run_id: Unique identifier for the DAG run

    Returns:
        JSON response with status
    """
    logger.error(f"Staging DAG failed - dag_run_id={dag_run_id}")

    # TODO: Cleanup ?


@router.post("/final/success")
async def final_success_callback(
    dag_run_id: str = Query(..., description="DAG run ID"),
    final_table_name: str = Query(..., description="Name of the final table"),
) -> None:
    """Callback when final_dag completes successfully.

    Args:
        dag_run_id: Unique identifier for the DAG run
        final_table_name: Name of the final table that was created

    Returns:
        JSON response with status
    """
    logger.info(f"Final DAG succeeded - dag_run_id={dag_run_id}, final_table={final_table_name}")

    # TODO: Update integrity_link table with last_retrieval_timestamp


@router.post("/final/failure")
async def final_failure_callback(
    dag_run_id: str = Query(..., description="DAG run ID"),
) -> None:
    """Callback when final_dag fails.

    Args:
        dag_run_id: Unique identifier for the DAG run

    Returns:
        JSON response with status
    """
    logger.error(f"Final DAG failed - dag_run_id={dag_run_id}")

    # TODO: Cleanup ?

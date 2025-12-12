"""Transformation task group."""

from typing import Any

from airflow.sdk import task, task_group
from data_manipulation.test import manipulate_data


@task_group(group_id="transformation")
def transformation_group() -> None:
    """Task group for transformation tasks.

    Tasks can access runtime configuration via context.
    """

    @task.branch(task_id="branching")
    def do_branching(**context: Any) -> str:
        params = context.get("params", {})
        print(params)
        return "branch_a"

    @task(task_id="transform_step_1")
    def transform_step_1(**context: Any) -> float:
        # Access params from context
        params = context.get("params", {})
        batch_size = params.get("batch_size", 100)
        environment = params.get("environment", "dev")

        print(f"Transform step 1 running in {environment} with batch_size={batch_size}")
        result = manipulate_data(1)
        print("transform_step_1:", result)
        return result

    @task(task_id="transform_step_2")
    def transform_step_2(**context: Any) -> float:
        # Access params from context
        params = context.get("params", {})
        enable_validation = params.get("enable_validation", True)

        print(f"Transform step 2 with validation={enable_validation}")
        result = manipulate_data(2)
        print("transform_step_2:", result)
        return result

    branching = do_branching()
    t1 = transform_step_1()
    t2 = transform_step_2()
    # Set up task dependencies
    _ = branching >> [t1, t2]

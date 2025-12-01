import os

from airflow.decorators import dag, task, task_group
from data_manipulation.test import manipulate_data


@dag(dag_id=os.path.basename(__file__).split(".")[0], schedule=None)
def task_flow() -> None:
    """
    This dag contains two dependent groups: the second group with
    independent tasks inside will run only after the first group
    with dependent tasks inside
    """

    @task_group(group_id="dependent_tasks")
    def run_dependent_tasks() -> None:
        @task(task_id="first_task")
        def first_task() -> None:
            print("2:", manipulate_data(2))
            print("First task")

        @task(task_id="second_task")
        def second_task() -> None:
            print("3:", manipulate_data(3))
            print("Second task")

        first_task() >> second_task()

    @task_group(group_id="independent_tasks")
    def run_independent_tasks() -> None:
        @task(task_id="task_a")
        def run_task_a() -> None:
            print("A:", manipulate_data(2 / 0))  # This will raise an exception
            print("Task A")

        @task(task_id="task_b")
        def run_task_b() -> None:
            print("5:", manipulate_data(5))
            print("Task B")

        run_task_a()
        run_task_b()

    run_dependent_tasks() >> run_independent_tasks()


task_flow()

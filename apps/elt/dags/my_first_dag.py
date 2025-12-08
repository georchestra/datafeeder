from datetime import datetime

from airflow.operators.empty import EmptyOperator

from airflow import DAG

with DAG(
    dag_id="my_first_dag",
    schedule="*/5 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["test"],
):
    EmptyOperator(task_id="hello")

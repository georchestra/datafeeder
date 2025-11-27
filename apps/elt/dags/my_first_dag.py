from datetime import datetime

from airflow import DAG

with DAG(
    dag_id="my_first_dag",
    schedule_interval="*/5 * * * *",  # every 5 minutes
    start_date=datetime.now(),
    catchup=False,
) as dag:
    print("Hello, Airflow!")
    pass

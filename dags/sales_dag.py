from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import os

# Configuration
INPUT_PATH = "/opt/airflow/data/input/sales_data.csv"
OUTPUT_PATH = "/opt/airflow/data/output/aggregated_sales.csv"

# Extract: Generate mock sales data
def generate_sales_data():
    data = [
        {"product": "Laptop", "quantity": 5, "price": 1000, "date": "2025-06-04"},
        {"product": "Laptop", "quantity": 3, "price": 1000, "date": "2025-06-04"},
        {"product": "Phone", "quantity": 10, "price": 500, "date": "2025-06-04"},
        {"product": "Phone", "quantity": 7, "price": 500, "date": "2025-06-04"},
        {"product": "Tablet", "quantity": 2, "price": 300, "date": "2025-06-04"}
    ]
    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(INPUT_PATH), exist_ok=True)
    df.to_csv(INPUT_PATH, index=False)
    return INPUT_PATH

# Transform: Aggregate sales data by product
def transform_sales_data(ti):
    input_file = ti.xcom_pull(task_ids='generate_sales')
    df = pd.read_csv(input_file)
    # Calculate total revenue (quantity * price) per product
    df['revenue'] = df['quantity'] * df['price']
    aggregated = df.groupby('product').agg({
        'quantity': 'sum',
        'revenue': 'sum'
    }).reset_index()
    return aggregated.to_dict('records')

# Load: Save aggregated data to CSV
def load_sales_data(ti):
    aggregated_data = ti.xcom_pull(task_ids='transform_sales')
    df = pd.DataFrame(aggregated_data)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    if os.path.exists(OUTPUT_PATH):
        df.to_csv(OUTPUT_PATH, mode='a', header=False, index=False)
    else:
        df.to_csv(OUTPUT_PATH, mode='w', header=True, index=False)

# Define the DAG
with DAG(
    dag_id='sales_etl_pipeline',
    start_date=datetime(2025, 6, 4),
    schedule_interval='@daily',
    catchup=False,
) as dag:

    # Task 1: Generate (Extract)
    generate_task = PythonOperator(
        task_id='generate_sales',
        python_callable=generate_sales_data,
    )

    # Task 2: Transform
    transform_task = PythonOperator(
        task_id='transform_sales',
        python_callable=transform_sales_data,
    )

    # Task 3: Load
    load_task = PythonOperator(
        task_id='load_sales',
        python_callable=load_sales_data,
    )

    # Set task dependencies
    generate_task >> transform_task >> load_task
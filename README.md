# Apache Airflow ETL Pipeline with Docker: A Hands-On Example

This project demonstrates a simple ETL (Extract, Transform, Load) pipeline using **Apache Airflow** and **Docker**. The pipeline processes mock sales data, showcasing Airflow's core concepts like DAGs, tasks, and XComs. It’s designed for beginners to learn how to set up and run an Airflow workflow in a Dockerized environment.

---

## 📋 Project Overview

The pipeline performs the following steps:
1. **Extract**: Generates mock sales data (e.g., product sales for a fictional store) and saves it as a CSV file.
2. **Transform**: Aggregates the data to calculate total quantity and revenue per product.
3. **Load**: Saves the aggregated results to a new CSV file.

This example uses Docker to set up Airflow with a PostgreSQL database, making it easy to run locally without complex installations.

---

## 📦 Prerequisites

Before starting, ensure you have:
- **Docker** and **Docker Compose** installed on your machine.
- Basic familiarity with terminal commands.

No external API keys or dependencies are required, as the project uses mock data.

---

## 📂 Project Structure

Create a directory named `airflow-sales/` with the following structure:

```
airflow-sales/
├── dags/
│   └── sales_dag.py      # The Airflow DAG definition
├── data/
│   ├── input/           # Directory for generated input CSV
│   └── output/          # Directory for output CSV
├── docker-compose.yml   # Docker Compose configuration
└── README.md            # This file
```

---

## 🚀 Setup Instructions

### 1. Create the Project Directory
Create the directory structure as shown above. You can do this manually or with the following commands:

```bash
mkdir -p airflow-sales/dags airflow-sales/data/input airflow-sales/data/output
cd airflow-sales
```

### 2. Set Up Docker Compose
Copy the following content into a file named `docker-compose.yml` in the `airflow-sales/` directory:

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_USER=airflow
      - POSTGRES_PASSWORD=airflow
      - POSTGRES_DB=airflow
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
    restart: always

  airflow-webserver:
    image: apache/airflow:2.7.3
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
    volumes:
      - ./dags:/opt/airflow/dags
      - ./data:/opt/airflow/data
    ports:
      - "8080:8080"
    command: webserver
    healthcheck:
      test: ["CMD-SHELL", "[ -f /opt/airflow/airflow-webserver.pid ]"]
      interval: 30s
      timeout: 30s
      retries: 3
    restart: always

  airflow-scheduler:
    image: apache/airflow:2.7.3
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
    volumes:
      - ./dags:/opt/airflow/dags
      - ./data:/opt/airflow/data
    command: scheduler
    restart: always

  airflow-init:
    image: apache/airflow:2.7.3
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      - AIRFLOW__CORE__EXECUTOR=LocalExecutor
      - AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
      - AIRFLOW__CORE__LOAD_EXAMPLES=False
    command: ["bash", "-c", "airflow db init && airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@example.com --password admin"]
    volumes:
      - ./dags:/opt/airflow/dags
      - ./data:/opt/airflow/data

volumes:
  postgres_data:
```

This file sets up:
- A PostgreSQL database for Airflow’s metadata.
- Airflow webserver (UI on port 8080).
- Airflow scheduler for task execution.
- An initialization service to set up the database and create an admin user (username: `admin`, password: `admin`).

### 3. Create the DAG File
Copy the following content into a file named `sales_dag.py` inside the `dags/` directory:

```python
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
```

This DAG defines three tasks:
- `generate_sales`: Creates mock sales data.
- `transform_sales`: Aggregates the data by product.
- `load_sales`: Saves the results to a CSV file.

---

## 🏃‍♂️ Running the Project

### 1. Start the Docker Containers
In the `airflow-sales/` directory, run:

```bash
docker-compose up -d
```

This starts the PostgreSQL database, Airflow webserver, scheduler, and initialization service.

### 2. Access the Airflow UI
- Open your browser and go to `http://localhost:8080`.
- Log in with:
  - **Username**: `admin`
  - **Password**: `admin`
- You should see the `sales_etl_pipeline` DAG listed in the “DAGs” view.

### 3. Install Required Dependencies (if needed)
The DAG uses the `pandas` library. If it’s not pre-installed in the Airflow image:
- Find the Airflow webserver container ID:
  ```bash
  docker ps
  ```
- Access the container:
  ```bash
  docker exec -it <airflow-webserver-container-id> bash
  ```
- Install `pandas`:
  ```bash
  pip install pandas
  ```
- Exit the container:
  ```bash
  exit
  ```

### 4. Trigger the DAG
- In the Airflow UI, toggle the `sales_etl_pipeline` DAG to “On” (switch on the left).
- Click the “Play” button (triangle icon) to trigger a manual run.
- Monitor the tasks in the “Graph” or “Grid” view to ensure they complete successfully.

### 5. Verify the Output
- Check the `data/output/` directory in your project folder.
- You should see a file named `aggregated_sales.csv` with content like:
  ```
  product,quantity,revenue
  Laptop,8,8000
  Phone,17,8500
  Tablet,2,600
  ```

---

## 🧹 Cleanup

To stop and remove the Docker containers:
```bash
docker-compose down
```

To remove the containers and the PostgreSQL data volume:
```bash
docker-compose down -v
```

---

## 📚 What You’ll Learn

By completing this project, you’ll gain hands-on experience with:
- Setting up Apache Airflow using Docker.
- Defining a DAG with tasks and dependencies.
- Using the `PythonOperator` to run custom Python code.
- Passing data between tasks with XCom.
- Scheduling and monitoring workflows via the Airflow UI.
- Persisting data using shared Docker volumes.

---

## 💡 Next Steps

Experiment with the following to deepen your understanding:
- **Modify the Data**: Add more products or randomize quantities in `generate_sales_data`.
- **Add Error Handling**: Include checks for file existence or data validation.
- **Use a Database**: Store the results in PostgreSQL using the `PostgresOperator`.
- **Explore Scheduling**: Change the `schedule_interval` to run the DAG more frequently (e.g., `@hourly`).

---

## 🛠️ Troubleshooting

- **DAG Not Visible in UI?** Ensure `sales_dag.py` is in the `dags/` folder, has no syntax errors, and the scheduler is running.
- **Tasks Failing?** Check the task logs in the Airflow UI (click on a task and select “Log”).
- **Permission Issues?** Ensure Docker has write access to the `data/` directory.

---

## 📜 License

This project is licensed under the MIT License. Feel free to use and modify it for learning purposes.

---

**Happy Learning with Apache Airflow! 🎉**
import database
import psycopg2
import time
import os
import logging

logging.basicConfig(level=logging.INFO)

# Wait for PostgreSQL to be ready
max_retries = 10
retry_delay = 5 # seconds

for i in range(max_retries):
    try:
        logging.info(f"Attempting to connect to DB (attempt {i+1}/{max_retries})...")
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres_db'),
            database=os.getenv('POSTGRES_DB', 'datavista_db'),
            user=os.getenv('POSTGRES_USER', 'datavista_api_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'DatavistaAPI@2025')
        )
        conn.close()
        logging.info("Successfully connected to DB.")
        break
    except psycopg2.OperationalError as e:
        logging.warning(f"DB connection failed: {e}. Retrying in {retry_delay} seconds...")
        time.sleep(retry_delay)
else:
    logging.error("Could not connect to PostgreSQL after multiple retries. Exiting.")
    exit(1)

# Create initial tables
try:
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        # Explicitly drop tables to ensure schema updates
        cursor.execute("DROP TABLE IF EXISTS csv_import_log CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS csv_summary_master_daily CASCADE;")
        conn.commit()
        logging.info("Existing tables dropped successfully (if they existed).")

        database.create_initial_tables(conn)
    logging.info("Database tables initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing database tables: {e}", exc_info=True)
    exit(1)
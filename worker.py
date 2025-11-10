import os
import logging
import json
import time
from redis import Redis
from app.database import SessionLocal
from app.anomaly_analyzer import analyze_anomaly_job

# Configure logging for the worker
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_conn = Redis(host=redis_host, port=int(redis_port))

# Name of the Redis list where Laravel will push JSON jobs
JOB_QUEUE_KEY = 'anomaly_analysis_queue_json'

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def process_job(job_payload: dict):
    """
    Processes a single job payload received from Redis.
    """
    execution_id = job_payload.get('execution_id')
    rules = job_payload.get('rules')

    if execution_id is None or rules is None:
        logger.error(f"Invalid job payload received: {job_payload}")
        return

    logger.info(f"Processing job for execution_id: {execution_id} with rules: {rules}")
    db_generator = get_db()
    db = next(db_generator)
    try:
        analyze_anomaly_job(execution_id, rules, db)
    except Exception as e:
        logger.error(f"Error in processing job for execution_id {execution_id}: {e}", exc_info=True)
    finally:
        try:
            db_generator.throw(None)
        except StopIteration:
            pass

if __name__ == '__main__':
    logger.info(f"Python worker started, polling Redis list: {JOB_QUEUE_KEY}")
    logger.info(f"Redis connection details: Host={redis_host}, Port={redis_port}, DB=0")
    logger.info(f"Redis connection object: {redis_conn}")
    while True:
        # Blocking pop from the list, waits for a job
        # timeout=1 means it will check every second, allowing for graceful shutdown
        popped_item = redis_conn.brpop(JOB_QUEUE_KEY, timeout=1)
        logger.info(f"brpop returned: {popped_item}")
        
        if popped_item: # Check if something was actually popped
            _, job_json = popped_item # Now it's safe to unpack
            logger.info(f"Received job_json: {job_json}")
            try:
                job_payload = json.loads(job_json)
                process_job(job_payload)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON job from Redis: {job_json}. Error: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unhandled error while processing job: {e}", exc_info=True)
        
        # Small delay to prevent busy-waiting if brpop returns None quickly
        # (though brpop with timeout already handles this to some extent)
        time.sleep(0.1)

import os
from redis import Redis
from rq import Worker, Queue

listen = ['default']
redis_host = os.getenv('REDIS_HOST', 'localhost') # Get REDIS_HOST from environment
redis_port = os.getenv('REDIS_PORT', '6379') # Get REDIS_PORT from environment
conn = Redis(host=redis_host, port=int(redis_port)) # Use host and port directly

if __name__ == '__main__':
    queues = [Queue(name, connection=conn) for name in listen]
    worker = Worker(queues, connection=conn)
    worker.work()
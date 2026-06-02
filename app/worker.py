import os
from redis import Redis
from rq import Worker

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

redis_conn = Redis.from_url(REDIS_URL)

if __name__ == "__main__":
    worker = Worker(queues=["default"], connection=redis_conn)
    worker.work()
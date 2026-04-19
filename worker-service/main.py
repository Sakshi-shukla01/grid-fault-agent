from __future__ import annotations
import os
import json
import asyncio
import redis.asyncio as aioredis
from pymongo         import MongoClient
from dotenv          import load_dotenv
from datetime        import datetime
from prometheus_client import Counter, start_http_server

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
MONGO_URI = os.environ["MONGO_URI"]

saved_counter  = Counter("worker_episodes_saved",  "Episodes saved to MongoDB")
errors_counter = Counter("worker_errors_total",    "Worker errors")

mongo  = MongoClient(MONGO_URI)
db     = mongo["gridfault"]
col    = db["episodes"]


async def handle_episode(data: dict) -> None:
    try:
        doc = {
            "task_id":     data.get("task_id"),
            "metadata":    data.get("metadata", {}),
            "faults":      data.get("faults", []),
            "final_score": data.get("metadata", {}).get("final_score"),
            "recall":      data.get("metadata", {}).get("recall"),
            "precision":   data.get("metadata", {}).get("precision"),
            "faults_found":data.get("metadata", {}).get("faults_found"),
            "total_faults":data.get("metadata", {}).get("total_faults"),
            "created_at":  datetime.utcnow()
        }
        col.insert_one(doc)
        saved_counter.inc()
        print(f"Saved episode — score: {doc['final_score']} "
              f"faults: {doc['faults_found']}/{doc['total_faults']}")
    except Exception as e:
        errors_counter.inc()
        print(f"Worker save error: {e}")


async def main() -> None:
    start_http_server(9101)
    print("Worker service started — listening on Redis episodes:complete")

    redis_client = aioredis.from_url(REDIS_URL)
    pubsub       = redis_client.pubsub()
    await pubsub.subscribe("episodes:complete")

    async for message in pubsub.listen():
        if message["type"] == "message":
            try:
                data = json.loads(message["data"])
                await handle_episode(data)
            except Exception as e:
                errors_counter.inc()
                print(f"Worker parse error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
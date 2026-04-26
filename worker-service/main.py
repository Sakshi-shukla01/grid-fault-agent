from __future__ import annotations
import os
import json
import redis
from pymongo  import MongoClient
from dotenv   import load_dotenv
from datetime import datetime

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
MONGO_URI = os.environ.get("MONGO_URI", "")

print("Worker starting...", flush=True)
print(f"REDIS_URL: {REDIS_URL}", flush=True)
print(f"MONGO_URI set: {bool(MONGO_URI)}", flush=True)

try:
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    mongo.server_info()
    db  = mongo["gridfault"]
    col = db["episodes"]
    print("MongoDB connected", flush=True)
except Exception as e:
    print(f"MongoDB failed: {e}", flush=True)
    col = None

try:
    r = redis.from_url(REDIS_URL, decode_responses=True)
    r.ping()
    print("Redis connected", flush=True)
except Exception as e:
    print(f"Redis failed: {e}", flush=True)
    exit(1)

pubsub = r.pubsub()
pubsub.subscribe("episodes:complete")
print("Listening on episodes:complete...", flush=True)

for message in pubsub.listen():
    print(f"Message: {message['type']}", flush=True)
    if message["type"] == "message":
        try:
            data = json.loads(message["data"])
            meta = data.get("metadata", {})
            print(f"Episode: {data.get('task_id')} score={meta.get('final_score')}", flush=True)
            if col is not None:
                doc = {
                    "task_id":     data.get("task_id"),
                    "model_name":  os.environ.get("MODEL_NAME", "unknown"),
                    "metadata":    meta,
                    "faults":      data.get("faults", []),
                    "final_score": meta.get("final_score"),
                    "recall":      meta.get("recall"),
                    "precision":   meta.get("precision"),
                    "efficiency":  meta.get("efficiency"),
                    "faults_found":meta.get("faults_found"),
                    "total_faults":meta.get("total_faults"),
                    "difficulty":  meta.get("task_difficulty"),
                    "completed":   True,
                    "created_at":  datetime.utcnow()
                }
                result = col.insert_one(doc)
                print(f"Saved: {result.inserted_id}", flush=True)
        except Exception as e:
            print(f"Error: {e}", flush=True)

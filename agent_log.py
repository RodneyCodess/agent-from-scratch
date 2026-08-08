import json
from datetime import datetime

LOG_PATH = f"logs/run-{datetime.now():%Y%m%d-%H%M%S}.jsonl"


def log(event, **fields):
    entry = {"ts": datetime.now().isoformat(), "event": event, **fields}
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

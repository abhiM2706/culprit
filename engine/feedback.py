"""
Feedback capture for the culpr.it weight-training loop.

Stores only self-reported data: the question/option trail already shown to
the user, the predicted category, and the user's own correctness judgment.
No passive signals, no free text beyond a category id, no inference beyond
what the user explicitly states -- consistent with the brief's
"only self-reported direct answers" constraint.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "data" / "feedback_log.jsonl"


def record_feedback(result, correct, actual_category=None, log_path=None):
    log_path = log_path or LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "session_id": result["session_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "predicted_category": result["category"],
        "confidence": result["confidence"],
        "questions_asked": result["questions_asked"],
        "trail": result["trail"],
        "feedback": {
            "correct": correct,
            "actual_category": actual_category,
        },
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_feedback(log_path=None):
    log_path = log_path or LOG_PATH
    if not log_path.exists():
        return []
    events = []
    with open(log_path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events

"""
Offline weight-training job for culpr.it (global aggregate scope, per
2026-08-29 design decision).

Reads accumulated self-reported feedback (data/feedback_log.jsonl) and
applies a small, bounded update to questions.json's `shifts` weights based on
which question/option choices preceded correct vs. incorrect diagnoses. Writes
a PROPOSED questions file + a human-readable diff report -- it never
overwrites the live questions.json. A human reviews and manually applies the
change, consistent with the brief's "taxonomy and question bank live in
versioned JSON... so they can be reviewed/edited without a redeploy."

Guardrails:
- Refuses to run below MIN_FEEDBACK_COUNT accumulated events, so a handful of
  early responses can't overfit the shared weights.
- Learning rate per event is small; every shift value is clamped to
  [MIN_SHIFT, MAX_SHIFT] so no single batch can swing weights drastically.
- Only mutates existing `shifts` values on the proposed copy. Never adds or
  removes categories, questions, or options -- that stays a manual edit to
  taxonomy.json / questions.json.
- Operates on the trail of question/option choices the user already made and
  their own correctness judgment -- no other data source.

Usage: python3 -m engine.train
"""

import copy
import json
from pathlib import Path

from engine.feedback import load_feedback

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = ROOT / "questions.json"
PROPOSED_PATH = ROOT / "questions.proposed.json"
REPORT_PATH = ROOT / "training_report.md"

MIN_FEEDBACK_COUNT = 30
LEARNING_RATE = 0.15
MIN_SHIFT = 0.5
MAX_SHIFT = 4.0


def clamp(x):
    return max(MIN_SHIFT, min(MAX_SHIFT, x))


def apply_update(questions_data, events):
    """Mutates questions_data['questions'][*]['options'][*]['shifts'] in place.
    Returns a list of (question_id, option_label, category, old, new) changes."""
    q_by_id = {q["id"]: q for q in questions_data["questions"]}
    changes = []

    for event in events:
        predicted = event["predicted_category"]
        fb = event["feedback"]
        correct = fb["correct"]
        actual = fb.get("actual_category")

        for step in event["trail"]:
            q = q_by_id.get(step["question_id"])
            if q is None:
                continue
            option = next((o for o in q["options"] if o["label"] == step["option_label"]), None)
            if option is None:
                continue

            if correct:
                # Reinforce the path that led to a correct diagnosis.
                if predicted in option["shifts"]:
                    old = option["shifts"][predicted]
                    new = clamp(old + LEARNING_RATE)
                    if new != old:
                        option["shifts"][predicted] = round(new, 3)
                        changes.append((q["id"], option["label"], predicted, old, new))
            else:
                # Weaken the path that led to a wrong diagnosis.
                if predicted in option["shifts"]:
                    old = option["shifts"][predicted]
                    new = clamp(old - LEARNING_RATE)
                    if new != old:
                        option["shifts"][predicted] = round(new, 3)
                        changes.append((q["id"], option["label"], predicted, old, new))
                # If the user told us the actual category, nudge toward it.
                if actual:
                    old = option["shifts"].get(actual, 0)
                    new = clamp(old + LEARNING_RATE) if old else 1.0
                    option["shifts"][actual] = round(new, 3)
                    changes.append((q["id"], option["label"], actual, old, new))

    return changes


def bump_version(version):
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def write_report(events, changes, report_path=REPORT_PATH):
    correct_n = sum(1 for e in events if e["feedback"]["correct"])
    lines = [
        "# culpr.it weight training report",
        "",
        f"Feedback events used: {len(events)} ({correct_n} correct, {len(events) - correct_n} incorrect)",
        f"Proposed shift changes: {len(changes)}",
        "",
        "| Question | Option | Category | Old | New |",
        "|---|---|---|---|---|",
    ]
    for qid, opt_label, cat, old, new in changes:
        lines.append(f"| {qid} | {opt_label} | {cat} | {old} | {new} |")
    lines.append("")
    lines.append(
        "Review this diff against `questions.json`, then manually replace it with "
        "`questions.proposed.json` if the changes look reasonable. This script never "
        "overwrites the live file."
    )
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    events = load_feedback()
    if len(events) < MIN_FEEDBACK_COUNT:
        print(f"Only {len(events)} feedback events, need {MIN_FEEDBACK_COUNT}+ to train. Skipping.")
        return

    with open(QUESTIONS_PATH) as f:
        original = json.load(f)
    proposed = copy.deepcopy(original)

    changes = apply_update(proposed, events)
    if not changes:
        print("No changes produced from current feedback batch.")
        return

    proposed["version"] = bump_version(proposed.get("version", "0.1.0"))

    with open(PROPOSED_PATH, "w") as f:
        json.dump(proposed, f, indent=2)
        f.write("\n")

    write_report(events, changes)
    print(f"Wrote {PROPOSED_PATH} and {REPORT_PATH}. Review before applying.")


if __name__ == "__main__":
    main()

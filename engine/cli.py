"""
Interactive CLI for locally exercising the culpr.it diagnostic session
engine and recording feedback. This is a dev/test harness, not the
production UI.

Usage:
  python3 -m engine.cli
  python3 -m engine.cli --repo /path/to/repo --path src/some/module
"""

import argparse

from engine.session import Session
from engine.feedback import record_feedback
from engine.repo_signals import collect_signals, apply_heuristic_rules


def run(repo=None, path=None):
    repo_prior, repo_notes = None, None
    if repo:
        signals = collect_signals(repo, subpath=path)
        repo_prior, repo_notes = apply_heuristic_rules(signals)

    s = Session(repo_prior=repo_prior, repo_notes=repo_notes)
    while not s.is_done():
        qid = s.next_question()
        if qid is None:
            break
        q = s.questions[qid]
        print(f"\n{q['prompt']}")
        for i, opt in enumerate(q["options"]):
            print(f"  {i + 1}. {opt['label']}")
        choice = input("> ").strip()
        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(q["options"])):
                raise ValueError
        except ValueError:
            print("Invalid choice, try again.")
            continue
        s.answer(qid, idx)

    result = s.result()
    print(f"\nculpr.it's guess: {result['label']}")
    print(f"Confidence: {result['confidence']}")
    print("Why:")
    for note in result["repo_signals"]:
        print(f"  - {note}")
    if result["trail"]:
        answer_summary = " -> ".join(f'"{step["option_label"]}"' for step in result["trail"])
        print(f"  - Your answers: {answer_summary}")
    print(f"Suggested next step: {result['suggested_action']}")

    fb = input("\nWas this right? (y/n/skip) ").strip().lower()
    if fb in ("y", "n"):
        correct = fb == "y"
        actual_category = None
        if not correct:
            actual_category = input("Which category id was actually right? (blank if unsure) ").strip() or None
        record_feedback(result, correct=correct, actual_category=actual_category)
        print("Feedback recorded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Path to a local git repo to pull starting signals from")
    parser.add_argument("--path", help="File or directory within --repo to scope signals to")
    args = parser.parse_args()
    run(repo=args.repo, path=args.path)

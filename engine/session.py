"""
culpr.it diagnostic session engine (Step 3).

Belief update: additive shifts over an initially uniform prior, normalized
to a probability distribution for confidence scoring.
Next-question selection: picks the unused question whose options most evenly
split weighted mass across the current top-N candidates (entropy heuristic) --
"simple heuristic fine for v1" per the build brief.
Stop rule: top category confidence >= STOP_CONFIDENCE, or MAX_QUESTIONS asked.
"""

import json
import math
import uuid
from pathlib import Path

STOP_CONFIDENCE = 0.55
MAX_QUESTIONS = 8
TOP_N_FOR_SPLIT = 6

ROOT = Path(__file__).resolve().parent.parent


def load_taxonomy(path=None):
    path = path or ROOT / "taxonomy.json"
    with open(path) as f:
        data = json.load(f)
    return {c["id"]: c for c in data["categories"]}


def load_questions(path=None):
    path = path or ROOT / "questions.json"
    with open(path) as f:
        data = json.load(f)
    return {q["id"]: q for q in data["questions"]}, [q["id"] for q in data["questions"]]


class Session:
    def __init__(self, taxonomy=None, questions=None, question_order=None,
                 repo_prior=None, repo_notes=None):
        """repo_prior: optional dict[category_id, float] of starting-weight
        nudges from repo-aware mode (Step 4). Kept separate from
        answer-driven shifts so the final result can show which weight came
        from repo signals vs. from the person's answers (auditability)."""
        self.taxonomy = taxonomy or load_taxonomy()
        if questions is None:
            questions, question_order = load_questions()
        self.questions = questions
        self.question_order = question_order
        self.repo_prior = repo_prior or {}
        self.repo_notes = repo_notes or []
        self.weights = {cat_id: 1.0 for cat_id in self.taxonomy}
        for cat_id, shift in self.repo_prior.items():
            if cat_id in self.weights:
                self.weights[cat_id] += shift
        self.asked = []   # question ids asked, in order
        self.trail = []   # [{"question_id":, "option_label":}]
        self.session_id = str(uuid.uuid4())

    def normalized(self):
        total = sum(self.weights.values())
        return {k: v / total for k, v in self.weights.items()}

    def top_confidence(self):
        norm = self.normalized()
        top_cat = max(norm, key=norm.get)
        return top_cat, norm[top_cat]

    def is_done(self):
        if len(self.asked) >= MAX_QUESTIONS:
            return True
        _, conf = self.top_confidence()
        return conf >= STOP_CONFIDENCE

    def _split_score(self, question):
        """Entropy of weighted mass each option pulls from the current top-N
        candidates. Higher entropy = the question splits current belief more
        evenly across its options = more informative to ask next."""
        norm = self.normalized()
        top_n = sorted(norm, key=norm.get, reverse=True)[:TOP_N_FOR_SPLIT]
        option_masses = []
        for opt in question["options"]:
            mass = sum(norm[c] for c in opt["shifts"] if c in top_n)
            option_masses.append(mass)
        total = sum(option_masses)
        if total <= 0:
            return -1.0  # question doesn't touch current top candidates at all
        probs = [m / total for m in option_masses if m > 0]
        return -sum(p * math.log2(p) for p in probs)

    def next_question(self):
        unused = [qid for qid in self.question_order if qid not in self.asked]
        if not unused:
            return None
        scored = [(qid, self._split_score(self.questions[qid])) for qid in unused]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def answer(self, question_id, option_index):
        question = self.questions[question_id]
        option = question["options"][option_index]
        for cat_id, shift in option["shifts"].items():
            self.weights[cat_id] = self.weights.get(cat_id, 1.0) + shift
        self.asked.append(question_id)
        self.trail.append({"question_id": question_id, "option_label": option["label"]})

    def result(self):
        top_cat, confidence = self.top_confidence()
        return {
            "session_id": self.session_id,
            "category": top_cat,
            "label": self.taxonomy[top_cat]["label"],
            "confidence": round(confidence, 4),
            "questions_asked": len(self.asked),
            "trail": self.trail,
            "repo_signals": self.repo_notes,
            "suggested_action": self.taxonomy[top_cat].get("suggested_action"),
        }

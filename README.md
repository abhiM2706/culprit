# culpr.it

An adaptive, elimination-style diagnostic engine that narrows down the root cause of
workplace and engineering friction across 14 taxonomy categories — usually in 8
questions or fewer.

Instead of a fixed questionnaire, each answer updates a belief distribution over
causes, and the next question is chosen to maximize expected information gain.

## How it works

1. **Belief state.** Every category starts with a prior (uniform, or informed by repo
   signals — see below). Each answer applies normalized belief-weight updates.
2. **Next-question selection.** Questions are scored by entropy reduction over the
   current belief state; the engine asks whichever question best splits the remaining
   candidates rather than walking a fixed order.
3. **Convergence.** The session ends once one category clears the confidence
   threshold, typically within ~8 questions.

## Taxonomy

The 14 categories are grounded in established occupational-psychology frameworks —
the Job Demands–Resources (JD-R) model, Herzberg's two-factor theory, and the Maslach
Burnout Inventory — rather than invented ad hoc. See [`taxonomy.json`](taxonomy.json).

## Repo-aware mode

Pointed at a local git repository, the engine pulls signals (commit frequency,
contributor count, presence of test coverage config and `CODEOWNERS`) and uses
heuristic rules to set diagnostic priors before the first question:

```bash
python3 -m engine.cli --repo /path/to/repo --path src/some/module
```

## Validation

The taxonomy was sanity-checked against the IBM HR Analytics Attrition dataset
(1,470 records) with correlation analysis and a Random Forest pass. Overtime and
workload came out as the strongest attrition predictor, with a
tenure/compensation/level cluster second — supporting the `workload_volume`,
`boundary_violation`, and `career_stagnation` categories as distinct and
well-founded. Full write-up, including where the data *contradicted* the initial
taxonomy: [`ANALYSIS.md`](ANALYSIS.md).

> The dataset is a public benchmark, not any real company's employee data. The
> analysis validates the taxonomy's structure; it is not a claim about anyone.

## Weight training

`engine/train.py` runs a human-reviewed pipeline: it reads feedback logs and proposes
bounded weight updates as a reviewable diff. Nothing is applied automatically.

## Running it

```bash
python3 -m engine.cli
```

The CLI is a dev harness for exercising the engine locally, not a production UI.

## Layout

| Path | What's in it |
|---|---|
| `engine/session.py` | Belief state, entropy-based question selection |
| `engine/repo_signals.py` | Git signal collection + heuristic priors |
| `engine/feedback.py` | Feedback capture |
| `engine/train.py` | Bounded weight-update proposals |
| `engine/cli.py` | Interactive dev harness |
| `taxonomy.json` | 14 categories and their framework grounding |
| `questions.json` | Question bank with per-option weight updates |
| `analysis/` | Validation scripts and outputs |

The IBM dataset itself is gitignored; `analysis/attrition_analysis.py` documents how
to fetch it via the Kaggle API.

# Data validation pass — IBM HR Analytics Attrition dataset

Source: [pavansubhasht/ibm-hr-analytics-attrition-dataset](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)
via Kaggle API. 1,470 employees, 35 variables, target = `Attrition` (Yes/No).
Attrition rate in the sample: 16.1% (237/1470).

Method: `analysis/attrition_analysis.py` — label-encode categoricals, then
(1) Pearson correlation of every feature against `Attrition`, and (2) a
Random Forest (500 trees, balanced class weight) feature-importance pass.
Full outputs: [`analysis/correlation_with_attrition.csv`](analysis/correlation_with_attrition.csv),
[`analysis/rf_feature_importance.csv`](analysis/rf_feature_importance.csv).

This is a **sanity check on the taxonomy**, not a claim about any real
company's employees. Purpose per the brief: confirm the taxonomy's
categories map to variables that carry real signal, rather than just
sounding plausible.

## Top correlates with attrition

| Variable | r | Taxonomy mapping |
|---|---|---|
| OverTime | **+0.246** | `workload_volume`, `boundary_violation` |
| TotalWorkingYears | -0.171 | `career_stagnation` |
| JobLevel | -0.169 | `career_stagnation` |
| MaritalStatus | +0.162 | (demographic — not actionable, not mapped) |
| YearsInCurrentRole | -0.161 | `career_stagnation`, `autonomy_loss` |
| MonthlyIncome | -0.160 | `career_stagnation` |
| Age | -0.159 | (proxy for tenure — not mapped directly) |
| YearsWithCurrManager | -0.156 | `manager_relationship` |
| StockOptionLevel | -0.137 | `career_stagnation` |
| YearsAtCompany | -0.134 | `career_stagnation` |
| JobInvolvement | -0.130 | `autonomy_loss`, `recognition_gap` |
| JobSatisfaction | -0.104 | `recognition_gap` |
| EnvironmentSatisfaction | -0.103 | `tooling_friction`, `autonomy_loss` |
| WorkLifeBalance | -0.064 | `boundary_violation` |
| RelationshipSatisfaction | -0.046 | `coworker_friction`, `manager_relationship` |

Random Forest importances broadly agree on the top cluster
(`MonthlyIncome`, `Age`, `OverTime`, tenure variables), confirming these
aren't just linear artifacts.

## What this confirms

1. **Workload/overtime is the single strongest predictor** in the dataset —
   directly validates putting `workload_volume` and `boundary_violation`
   under the JD-R "demands" branch and giving the Q1 domain split real
   weight on that side.
2. **A cluster of tenure/level/comp variables** (`TotalWorkingYears`,
   `JobLevel`, `MonthlyIncome`, `YearsAtCompany`, `StockOptionLevel`)
   moves together and is the second-strongest signal — validates
   `career_stagnation` as a distinct, well-supported category.
3. **Manager tenure and relationship/job satisfaction scores carry real
   but weaker signal** — supports keeping `manager_relationship`,
   `coworker_friction`, and `recognition_gap` as separate categories
   rather than collapsing them, but their questions shouldn't be
   over-weighted relative to workload/career questions.

## What this contradicts / where the taxonomy needed adjusting

- **`YearsSinceLastPromotion` is nearly uncorrelated with attrition**
  (r = -0.033) — the literal "years since last promotion" metric is a
  weak proxy for stagnation, despite being the intuitive HR variable for
  it. `TrainingTimesLastYear` is similarly weak (r = -0.06). **Consequence
  for questions.json**: `career_stagnation` and `skill_mismatch` questions
  are phrased experientially ("do you see a path to grow," "do you feel
  equipped for what's asked of you") rather than around promotion-timing
  or training-count, since those literal counters don't carry signal here.
- **Demographic variables** (`MaritalStatus`, `Age`, `Gender`) show up
  with non-trivial correlation but aren't actionable root causes — they
  were **not** mapped to any taxonomy category, since culpr.it outputs a
  suggested action, and "you are young and unmarried" isn't one.

## Coverage gap: this dataset only validates half the taxonomy

The IBM dataset is a general-workforce HR dataset — it has no variables
for engineering-specific root causes: `tech_debt`, `ownership_gap`,
`process_bottleneck`, `knowledge_silo`, `tooling_friction`. Those five
categories remain grounded in JD-R theory (demands side: broken
tools/process as a workload multiplier) but are **not** validated against
real attrition data here. This is flagged so it isn't misrepresented as
data-backed when it's theory-only for now. If the burnout dataset
(mental fatigue / burn rate target) is pulled in later, it's a better fit
for validating the Maslach-derived exhaustion/cynicism split, still not
for the engineering branch.

## Categories kept as-is, unchanged by this pass

`task_ambiguity`, `autonomy_loss`, `boundary_violation`,
`skill_mismatch` — directionally consistent with weaker but present
correlates (`EnvironmentSatisfaction`, `JobInvolvement`,
`WorkLifeBalance`), no evidence to drop or merge them.

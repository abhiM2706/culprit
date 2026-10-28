"""
Correlation / feature-importance pass on the IBM HR Analytics Attrition
dataset, used to sanity-check the culpr.it taxonomy against real
(if synthetic) organizational data. See ../ANALYSIS.md for the writeup.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

df = pd.read_csv("data/WA_Fn-UseC_-HR-Employee-Attrition.csv")

# Drop constant / non-informative columns
df = df.drop(columns=["EmployeeCount", "StandardHours", "Over18", "EmployeeNumber"])

target = "Attrition"
y = (df[target] == "Yes").astype(int)
X = df.drop(columns=[target])

# Encode categoricals
cat_cols = X.select_dtypes(include="object").columns
X_enc = X.copy()
for c in cat_cols:
    X_enc[c] = LabelEncoder().fit_transform(X_enc[c])

# --- Point-biserial-style correlation of each feature with attrition ---
corr = X_enc.assign(Attrition=y).corr(numeric_only=True)["Attrition"].drop("Attrition")
corr_sorted = corr.reindex(corr.abs().sort_values(ascending=False).index)

# --- Random Forest feature importance ---
rf = RandomForestClassifier(n_estimators=500, random_state=42, class_weight="balanced")
rf.fit(X_enc, y)
importances = pd.Series(rf.feature_importances_, index=X_enc.columns).sort_values(ascending=False)

print("Attrition rate:", round(y.mean(), 4), f"({y.sum()} of {len(y)})")
print("\n=== Top 15 by |correlation| with Attrition ===")
print(corr_sorted.head(15).round(4).to_string())

print("\n=== Top 15 by Random Forest importance ===")
print(importances.head(15).round(4).to_string())

# Save to files for the writeup
corr_sorted.round(4).to_csv("analysis/correlation_with_attrition.csv", header=["correlation"])
importances.round(4).to_csv("analysis/rf_feature_importance.csv", header=["importance"])

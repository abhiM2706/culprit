"""
Repo-aware mode (Step 4) -- local git only, per 2026-08-30 design decision.

Collects technical/process signals from a local git repo via plain `git`
subprocess calls: commit frequency, contributor count, and test-coverage
config presence, scoped to an optional path within the repo. No network
calls, no tokens.

Explicitly NOT collected, per the brief's hard constraint (repo-aware mode
signals are technical/process only): commit messages, diff contents, PR/issue
descriptions, or any personal communications data. PR/issue age is also not
available since this is local-git-only (no GitHub API) -- see brief Step 4;
that signal is simply omitted rather than approximated.

Signals feed a small, fixed set of heuristic rules (see RULES below) that
produce a *starting* belief-weight nudge per category -- they set the prior,
they never replace question-based narrowing. Every rule that fires is
recorded as a human-readable note so the final output can show exactly which
weight came from repo signals vs. from the person's answers (auditability
requirement in the brief).
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

STALE_WINDOW_DAYS = 90
HIGH_CHURN_COMMIT_THRESHOLD = 20
SOLE_CONTRIBUTOR_THRESHOLD = 1

COVERAGE_CONFIG_FILENAMES = [
    ".coveragerc",
    "pytest.ini",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.js",
    "vitest.config.ts",
    "codecov.yml",
    ".codecov.yml",
]

CODEOWNERS_PATHS = ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"]


@dataclass
class RepoSignals:
    commit_count: int
    contributor_count: int
    has_coverage_config: bool
    has_codeowners: bool
    scanned_path: str


def _run_git(repo_path, args):
    result = subprocess.run(
        ["git", "-C", str(repo_path)] + args,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _is_git_repo(repo_path):
    out = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    return out == "true"


def collect_signals(repo_path, subpath=None, window_days=STALE_WINDOW_DAYS):
    """Collect raw repo signals. `subpath` scopes commit/contributor counts
    to a file or directory within the repo (e.g. a module under review);
    defaults to the whole repo if omitted."""
    repo_path = Path(repo_path)
    if not _is_git_repo(repo_path):
        raise ValueError(f"{repo_path} is not a git repository")

    path_args = ["--", subpath] if subpath else []

    log_out = _run_git(
        repo_path,
        ["log", f"--since={window_days} days ago", "--pretty=format:%an"] + path_args,
    )
    lines = [l for l in log_out.splitlines() if l.strip()]
    commit_count = len(lines)
    contributor_count = len(set(lines))

    has_coverage_config = any(
        (repo_path / fname).exists() for fname in COVERAGE_CONFIG_FILENAMES
    )
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists() and "[tool.coverage" in pyproject.read_text(errors="ignore"):
        has_coverage_config = True
    package_json = repo_path / "package.json"
    if package_json.exists():
        text = package_json.read_text(errors="ignore")
        if '"jest"' in text or '"nyc"' in text or '"c8"' in text:
            has_coverage_config = True

    has_codeowners = any((repo_path / p).exists() for p in CODEOWNERS_PATHS)

    return RepoSignals(
        commit_count=commit_count,
        contributor_count=contributor_count,
        has_coverage_config=has_coverage_config,
        has_codeowners=has_codeowners,
        scanned_path=subpath or "(whole repo)",
    )


def apply_heuristic_rules(signals: RepoSignals, window_days=STALE_WINDOW_DAYS):
    """Small, fixed, auditable rule set mapping raw signals to starting
    category weight nudges. Returns (shifts: dict[category_id, float],
    notes: list[str])."""
    shifts = {}
    notes = []

    def bump(cat_id, amount):
        shifts[cat_id] = shifts.get(cat_id, 0) + amount

    if signals.commit_count > 0 and signals.contributor_count <= SOLE_CONTRIBUTOR_THRESHOLD:
        bump("knowledge_silo", 2)
        bump("ownership_gap", 1)
        notes.append(
            f"Repo signal: only {signals.contributor_count} contributor to "
            f"{signals.scanned_path} in the last {window_days} days"
        )

    if signals.commit_count == 0:
        bump("tech_debt", 2)
        notes.append(
            f"Repo signal: no commits to {signals.scanned_path} in the last "
            f"{window_days} days -- may be stale or risky to touch"
        )
    elif signals.commit_count >= HIGH_CHURN_COMMIT_THRESHOLD:
        bump("process_bottleneck", 1)
        bump("workload_volume", 1)
        notes.append(
            f"Repo signal: high commit churn ({signals.commit_count} commits) "
            f"in {signals.scanned_path} in the last {window_days} days"
        )

    if not signals.has_coverage_config:
        bump("tech_debt", 1)
        bump("process_bottleneck", 1)
        notes.append("Repo signal: no test-coverage configuration detected in repo")

    if not signals.has_codeowners:
        bump("ownership_gap", 2)
        notes.append("Repo signal: no CODEOWNERS file found -- no explicit ownership mapping")

    return shifts, notes

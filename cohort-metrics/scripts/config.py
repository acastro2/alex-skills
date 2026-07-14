"""Shared config + window computation for the cohort-metrics pipeline.

All scripts import this so the analysis windows are computed identically and,
crucially, RELATIVE TO TODAY. That's what makes a weekly re-run just work:
nothing is hardcoded to a calendar date except `beta_start` (the kickoff), which
is a real fixed event.

Config resolution order for both the config file and the output dir:
  explicit argv -> environment variable -> sensible default in the cwd.
"""
import json
import os
import sys
from datetime import date, timedelta


def resolve_paths(argv):
    """(config_path, out_dir) from argv[1], argv[2], env, or defaults."""
    cfg = (argv[1] if len(argv) > 1 else None) \
        or os.environ.get("COHORT_CONFIG") or "cohort-config.json"
    out = (argv[2] if len(argv) > 2 else None) \
        or os.environ.get("COHORT_OUT") or "cohort-out"
    os.makedirs(out, exist_ok=True)
    return cfg, out


def load(cfg_path):
    if not os.path.exists(cfg_path):
        sys.exit(f"Config not found: {cfg_path}\n"
                 f"Copy references/roster.example.json and edit it.")
    return json.loads(open(cfg_path).read())


def windows(cfg):
    """Compute all analysis windows from today() and the configured kickoff.

    - snapshot: the recent `snapshot_weeks` window, used for cohort-vs-rest.
    - before/after: split at `beta_start`. `after` GROWS every week you re-run,
      so the early-signal caveat weakens on its own over time (that is the point).
    - full: earliest date any collector needs to pull (covers before + snapshot).
    """
    today = date.today()
    # allow a pinned date for reproducible re-runs / tests
    if cfg.get("today"):
        today = date.fromisoformat(cfg["today"])
    beta = date.fromisoformat(cfg["beta_start"])
    snap_weeks = cfg.get("snapshot_weeks", 13)
    base_weeks = cfg.get("baseline_weeks", 13)
    snapshot_start = today - timedelta(weeks=snap_weeks)
    before_start = beta - timedelta(weeks=base_weeks)
    full_start = min(snapshot_start, before_start)
    after_weeks = max((today - beta).days / 7, 0.01)
    return {
        "today": today.isoformat(),
        "beta_start": beta.isoformat(),
        "snapshot_start": snapshot_start.isoformat(),
        "before_start": before_start.isoformat(),
        "full_start": full_start.isoformat(),
        "weeks": {
            "snapshot": round((today - snapshot_start).days / 7, 2),
            "before": round((beta - before_start).days / 7, 2),
            "after": round(after_weeks, 2),
        },
    }

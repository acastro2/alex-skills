# Audit

How `scripts/ci_audit.py` splits CI time, and what its numbers do not show. Checked 2026-11-24.

## The three buckets

| Bucket | Measured as | Source field |
| --- | --- | --- |
| Waiting | job `started_at` minus job `created_at` | [jobs API](https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2026-03-10) |
| Setup | the sum of setup step durations: "Set up job", checkout, `setup-*`, install, cache and restore steps | step `started_at` and `completed_at` |
| Running | job duration minus setup | job `completed_at` minus `started_at`, minus setup |

The setup step names are one regex at the top of the script. Edit it when a repo names its install step something else, and say so in the report.

**PR wall time** is the latest job `completed_at` minus the run `created_at`. That is the time a PR waits for its result, and it is the number the 1-minute and 2-minute targets measure.

## Commands

```bash
python3 -I scripts/ci_audit.py OWNER/REPO --runs 150
python3 -I scripts/ci_audit.py OWNER/REPO --runs 150 --event pull_request --json before.json
```

Run it once before a change and once on the change's own runs, and put both tables in the PR.

## Limits

- **Percentiles are computed by the script.** The REST API has no percentile fields. [github-actions-profiler](https://github.com/utgwkk/github-actions-profiler) reports p50 to p99 per job and step, if you need a second opinion.
- **Cancelled and skipped runs are left out.** A cancelled run is not a pass.
- **Only the latest attempt of a run counts.** A run that needed a re-run attempt is a failure hidden by a retry: count those separately and treat each one as a bug.
- **A run whose jobs GitHub cannot return is skipped, with a warning.** The script retries an HTTP 5xx or a stream reset three times, then skips the run and lists it. It also warns when it found fewer runs than you asked for. Report both numbers: a sample with many skipped runs is biased.
- **Big audits take minutes.** 120 runs of astral-sh/uv (14,665 jobs) took about 215 s with 8 parallel calls.
- **Billed minutes are estimated.** GitHub rounds each job up to a whole minute; some third-party runners bill by the second.

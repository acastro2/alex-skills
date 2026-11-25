# Python

Default tools for the budgets in `improve-cicd`. Checked 2026-11-24 (uv 0.13.9, ruff 0.17.6, pytest-xdist 3.8.0). Check each command against the installed version before you use it.

| Job | Command | Notes |
| --- | --- | --- |
| Setup | `astral-sh/setup-uv` with `enable-cache: true`, pinned to a commit | Installs uv and keeps its cache ([uv in GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)) |
| Python | `uv python install` | Installs the version the project pins |
| Install | `uv sync --locked` | Fails if `uv.lock` is stale. `--frozen` is faster but can miss a new dependency, so it is "checking less" ([sync](https://docs.astral.sh/uv/concepts/projects/sync/)) |
| Run without re-sync | `uv run --no-sync <cmd>` | Skips the second freshness check after `uv sync` |
| Cache size | `uv cache prune --ci` | Run at the end of the job, before the cache is saved |
| Lint | `ruff check .` | Turn on every rule you can. `--select ALL` also turns on new rules at every upgrade; that is fine under "never check less", but pin the ruff version ([linter](https://docs.astral.sh/ruff/linter/)) |
| Format | `ruff format --check .` | Import sorting is a lint rule (`I`), not part of `ruff format` ([formatter](https://docs.astral.sh/ruff/formatter/)) |
| Typecheck | `ty check`, or `pyrefly check` | See the warning below |
| Tests | `uv run --no-sync pytest -n auto` | With pytest-randomly installed, every run is in random order. `-n auto` uses physical cores. On a small suite, worker startup can cost more than it saves: measure a fixed `-n 4` too ([xdist](https://pytest-xdist.readthedocs.io/en/latest/distribution.html)) |
| Slow tests | `pytest --durations=10 --durations-min=1.0` | Finds the files over the 20-second split limit |

## Typecheck: ty and Pyrefly are pre-stable

- **ty** is in beta, still release `0.0.x` (0.0.109 on 2026-11-23). Astral reports 10–60× faster than mypy and Pyright, a vendor benchmark ([ty](https://astral.sh/blog/ty), [releases](https://github.com/astral-sh/ty/releases)).
- **Pyrefly** 1.5 reports 13× faster than mypy and 25× faster than Pyright on 18 projects, and about even with ty ([Pyrefly 1.5](https://pyrefly.org/blog/v1.5/)).
- Before you replace mypy or Pyright, run both on the whole repo and list every error the new checker misses. A missed error class is "checking less": keep the old checker for it.

## Isolation and order

- xdist workers are separate processes, but they share databases, files, and ports. Name each resource with the `worker_id` fixture, and each run with `testrun_uid` ([xdist how-to](https://pytest-xdist.readthedocs.io/en/latest/how-to.html)).
- **pytest-randomly** shuffles modules, classes, and tests, and reseeds random before each test. It turns on when installed. Replay a failure with `pytest --randomly-seed=last` ([pytest-randomly](https://github.com/pytest-dev/pytest-randomly)).
- `--dist loadfile` keeps a file on one worker, for shared file fixtures; `--dist worksteal` evens out uneven files. Pick one.

## Shards

pytest-split balances shards from recorded times ([pytest-split](https://github.com/jerry-git/pytest-split/)):

```bash
pytest --store-durations                 # on main, every full run; save .test_durations
pytest --splits 4 --group 1              # on each shard, with the same .test_durations
```

New tests get an average time, so refresh the durations file from main. Prove the shards together ran every test: compare the collected test IDs of all shards with `pytest --collect-only -q`.

## Test selection

pytest-testmon picks the tests affected by the changed code from its `.testmondata` ([testmon](https://www.testmon.org/)):

```bash
pytest --testmon            # PRs: run only what the diff can reach
```

It does not track static files or external services. List those as inputs that rerun everything, and run the full suite in the merge queue.

## Never in a required check

`pytest-rerunfailures` and `--reruns`: a retry hides the bug.

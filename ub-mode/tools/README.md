# ub-mode tools

The three tools `../SKILL.md` names: `crapper`, `dryer`, and `mutator`, by Uncle Bob.
Each one is checked out here at a pinned commit and installed into one shared
virtualenv, so the whole skill is this folder and nothing else on the machine.

| Tool | Upstream | Pinned commit | What it does |
| --- | --- | --- | --- |
| `crapper` | github.com/unclebob/crapper | `6fd92c4` | CRAP score per function: cyclomatic complexity weighted by test coverage |
| `dryer` | github.com/unclebob/dryer | `66ff6d2` | Structural duplicate candidates, scored by Jaccard similarity |
| `mutator` | github.com/unclebob/mutator | `a5a0cb8` | Mutation testing: kills survivors, finds uncovered code |

All three are 0BSD. Each reads Clojure, Java, Go, TypeScript, Rust, and Python, and
each writes a snapshot under `.metrics/` in the target repo.

## Layout

```
tools/
├── setup.sh     # clone the three at the pins, build .venv, install all three
├── bin/         # crapper, dryer, mutator wrappers (self-healing: runs setup.sh once)
├── src/         # the three checkouts (git-ignored, rebuilt by setup.sh)
└── .venv/       # one shared virtualenv (git-ignored)
```

`mutator` imports `crapper` from the environment. Installing both into one venv
satisfies that, so no sibling layout is needed.

## Install

```bash
~/.agents/skills/ub-mode/tools/setup.sh
```

Needs Python 3.11 or newer. Takes about 20 s and 20 MB. Re-run it after changing a pin.

## Run

Point them at a repo root. Each one finds the language per file by itself.

```bash
tools/bin/crapper                                  # CRAP report, writes .metrics/crap.edn
tools/bin/crapper --no-coverage src                # complexity only
tools/bin/crapper --changed                        # git additions and edits
tools/bin/dryer --threshold 0.8 src                # duplicate candidates, .metrics/dry.edn
tools/bin/mutator --scan src                       # list mutation sites, run nothing
tools/bin/mutator --test-command "pytest -q" src   # mutate and run the tests
```

## Python gotchas

- **Give mutator the test command.** Without `--test-command` it runs `unittest
  discover` in its own interpreter, which misses a pytest suite and misses the
  project's dependencies. `--test-command "pytest -q"` is the reliable form.
- **crapper and dryer pick the interpreter themselves.** crapper installs
  `coverage` and (when the project has none) `pytest` into the project
  interpreter it finds. A `tests/` folder without `__init__.py` makes it fall back
  to `unittest discover` and report `NO TESTS RAN`, so coverage reads 0%. A
  `conftest.py` or a `pyproject.toml` fixes that.
- **First mutator run is the slow one.** It executes every covered mutant. Start
  with the file you are working on. Later runs are differential and only rerun
  survivors plus functions whose text changed.

## Updating a pin

```bash
cd tools/src/<tool> && git fetch --depth 1 origin <commit>
```

Then edit the `PINS` block in `setup.sh`, delete `.venv`, and run `setup.sh` again.

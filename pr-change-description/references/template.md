# Change description template (medium and large PRs)

For a small PR, use the short shape in `../SKILL.md` instead. Copy this skeleton, then replace every `<...>` with a fact from the code. Delete a section that has nothing true to say; never fill one with filler.

````markdown
This PR <does what, in one sentence>. It is <N> files, but <M> of those are <fixtures / snapshots / generated>. Production code is <K> files (+<a> / -<d>).

This description has one section per area. Each section gives the reason for the change, a before and after diagram, and what to check. The plan and decisions are in `<path to spec or ADR>`.

## The whole change

### Before

```mermaid
flowchart TB
  <every module involved, grouped in subgraphs, with the pain on the edges>
```

### After

```mermaid
flowchart TB
  <the new modules as subgraphs, the callers outside, the one interface on the edges>
```

### Size of the key files

| File | Before | After | Why |
| --- | --- | --- | --- |
| `<path>` | <lines> | <lines / deleted / moved> | <one line> |

## 1. <Area name>: <the deepening in a few words>

### Why

<One sentence on the pain, then bullets with concrete drift:>

- <Copy A does X, copy B does Y.>
- <A failure that is possible today, in plain words.>

### Before

```mermaid
<flowchart of this area, problem labels on the edges>
```

### After

```mermaid
<flowchart of this area, the seam in a subgraph>
```

### <One call / the failure path> after the change

```mermaid
sequenceDiagram
  <participants, the ordered calls, an alt block for the failure branch>
```

### What to check

- `<file>` (<lines>): <what to read for>.
- `<test or snapshot path>`: <what it proves, and what is byte-identical>.

<Repeat for each area.>

## Behaviour changes

Everything else stays identical. <How that is proven, in one line.>

| # | Change | Who notices |
| --- | --- | --- |
| <n> | <the change> | <which users or operators> |

<Changes that were proposed and withdrawn, in one line each.>

## How the safety was proven

```mermaid
flowchart LR
  <base> --> <characterization or tests first> --> <decisions recorded> --> <refactor commits> --> <check: diff mapped to an intended change>
```

- <Unit tests: measured count, and the count on the base branch.>
- <Integration or end-to-end runs: what, where, the result.>
- <New tests per area: a table if there are more than three areas.>

## Review path

Read the commits in order. <Each one passes the suite on its own, if true.>

| Commits | What | Read |
| --- | --- | --- |
| `<sha>`, `<sha>` | <what the group does> | <the files or snapshots to open> |

Skip `<fixture paths>` except where a step above points to it.

## Things to watch after deploy

- <A real operational change, a new refusal, or a migration step.>
````

## Notes per section

- **Opener.** Lead with the size split. A reviewer who sees "711 files" and nothing else assumes the worst.
- **Size table.** Pick the files a reviewer would ask about: the ones that shrank, grew, moved, or were deleted. Five to eight rows.
- **Why.** Concrete beats general. "REST search takes 7 params, MCP takes 4" beats "the surfaces were inconsistent".
- **What to check.** Point at the smallest file that holds the seam, then at the test that proves the behaviour.
- **Behaviour changes.** Number them the same way as the spec, so a reviewer can cross-check.
- **Review path.** Group commits by step. Say what to read in each group, including "the import diff only" for a pure move.

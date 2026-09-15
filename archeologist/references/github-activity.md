# SOURCE I: GitHub activity (SECONDARY; PRIMARY for shipped-work questions)

PRs you authored or reviewed, their discussions, and your commits across ALL orgs and repos.
This is the record of what actually LANDED — a merged PR or a commit is harder evidence than any
transcript. Query it with the first-party `gh` CLI (no MCP). READ-ONLY: only `search`, `view`,
and read-only `api` GET calls — never create/edit/close/comment/merge/approve/request-changes,
never anything that writes to GitHub.

## Availability check (do this first, cheaply)

```bash
gh --version && gh auth status
```

If not installed or not authenticated, report "GitHub store unavailable this session" in NO DATA
and move on. Never treat unavailability as "no results".

> **Multi-account gotcha:** `@me` resolves against the ACTIVE `gh` account (currently
> `AlexandreCastro_attain`; verified 2026-08-21). A second account (`acastro2`) may also be logged
> in but inactive — when hunting history from the other identity, pass the login explicitly
> (e.g. `--author acastro2`) instead of `@me`.

All strategies below take a date window. For "past week": `SINCE=$(date -v-7d +%Y-%m-%d)`
(macOS BSD date). Results cover every repo the token can see, including private org repos
(token scopes include `repo` + `read:org`).

## Strategy I1: PRs I authored in a window (primary shipped-work scan)

The CLI equivalent of the web UI query `is:pr author:@me sort:updated-desc`:
```bash
SINCE=$(date -v-7d +%Y-%m-%d)
gh search prs --author "@me" --updated ">=$SINCE" --sort updated --limit 50 \
  --json number,title,repository,url,state,updatedAt \
  --jq '.[] | "\(.updatedAt[0:10]) [\(.state)] \(.repository.nameWithOwner)#\(.number) \(.title[0:80])\n  \(.url)"'
```
Drop `--updated` for all-time. Add a keyword argument for topical search:
`gh search prs --author "@me" snowflake --sort updated --limit 10 ...` (same JSON flags).

## Strategy I2: PRs I reviewed (decisions I shaped but did not author)
```bash
SINCE=$(date -v-7d +%Y-%m-%d)
gh search prs --reviewed-by "@me" --updated ">=$SINCE" --sort updated --limit 20 \
  --json number,title,repository,url,state \
  --jq '.[] | "\(.repository.nameWithOwner)#\(.number) [\(.state)] \(.title[0:80])\n  \(.url)"'
```

## Strategy I3: Commits in a window (what landed, including non-PR pushes)
```bash
SINCE=$(date -v-7d +%Y-%m-%d)
gh api -X GET search/commits -f q="author:@me committer-date:>=$SINCE" \
  -f sort=committer-date -f order=desc -f per_page=50 \
  --jq '(.total_count|tostring)+" commits", (.items[] | "\(.commit.author.date[0:10]) \(.repository.full_name)@\(.sha[0:7]) \(.commit.message | split("\n")[0] | .[0:80])")'
```
Caveat: the commit search index lags slightly and covers indexed branches; cross-check a specific
repo with local `git log --all --author=<login> --since="$SINCE"` when it matters.

## Strategy I4: Read a PR's full context (body + discussion = where decisions live)
```bash
gh pr view https://github.com/<org>/<repo>/pull/<N> \
  --json title,state,mergedAt,body,comments \
  --jq '"\(.title) [\(.state)] merged \(.mergedAt[0:10])", "BODY: \(.body[0:600])", (.comments[] | "\(.createdAt[0:10]) <\(.author.login)> \(.body[0:300])")'
```
The PR body and comment thread usually state WHY a change was made — pair it with the transcript
that produced it for the full narrative.

## Citation format
- PRs: `GitHub: <org>/<repo>#<N> "<title>" (<state>, YYYY-MM-DD)` (include URL)
- Commits: `GitHub: <repo>@<sha7> "<first line of message>" (YYYY-MM-DD)`

## Guardrail specifics for this store
- Strictly read-only against GitHub: no comment/approve/merge/label/close, no gist creation, no
  reactions. The briefing quotes from PRs; it never touches them.
- PR comments may contain other people's writing: quote the minimum needed as evidence.
- CI bot spam (coverage reports, dependabot) floods comment threads — filter by human authors
  when reading a discussion.

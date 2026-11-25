# Go

Default tools for the budgets in `improve-cicd`. Checked 2026-11-24 (Go 1.27.4, golangci-lint v2.15.0, gotestsum v1.13.0). Check each command against the installed version before you use it.

| Job | Command | Notes |
| --- | --- | --- |
| Setup | `actions/setup-go@v7` with `go-version: '1.27.4'` | Caches both `GOMODCACHE` and `GOCACHE` by default. For more than one module, set `cache-dependency-path: "**/go.sum"` ([setup-go](https://github.com/actions/setup-go/blob/main/README.md)) |
| Lint and format | `golangci-lint run ./...` | v2 config: `govet` and `staticcheck` under `linters`, `gofmt` and `gofumpt` under `formatters`. Check the file with `golangci-lint config verify` ([install](https://golangci-lint.run/docs/welcome/install/local/)) |
| Format diff | `golangci-lint fmt --diff ./...` | Shows what would change; `gofumpt -l .` lists files ([gofumpt](https://github.com/mvdan/gofumpt)) |
| Typecheck | `go vet ./...` | Builds and type-checks; `go test` runs only a subset of vet ([go command](https://go.dev/cmd/go/)) |
| PR tests | `go test ./...` | Package-list mode caches passing packages, so unchanged packages print `(cached)` |
| Full suite | `go test -count=1 -shuffle=on ./...` | `-count=1` forces a real run; `-shuffle=on` prints its seed, replay with `-shuffle=<seed>` |
| Race | `go test -race -count=1 ./...` | 2–20× slower and 5–10× more memory: its own job, in the merge queue. `-count=1`, because `-race` alone can return a cached pass ([race detector](https://go.dev/doc/articles/race_detector)) |

## The cache and "never hide failures"

- **A cached pass is a real pass** for the same test binary, flags, files, and environment. The cacheable test flags are `-benchtime`, `-coverprofile`, `-cpu`, `-failfast`, `-fullpath`, `-list`, `-outputdir`, `-parallel`, `-run`, `-short`, `-skip`, `-timeout`, `-v` ([go command](https://go.dev/cmd/go/)).
- **`-race`, `-json`, and `-p` still cache:** on Go 1.27.4, a second `go test -race ./...` printed `(cached)` (reviewer run, 2026-11-25). `-race` builds a different binary, so it caches separately. Of the four, only `-shuffle` forced a re-run. **Use `-count=1` for a real, uncached run.**
- **The cache does not see files outside Go's view**, such as a database the test reaches. So the merge queue runs `-count=1 -shuffle=on`, uncached.
- **Never `-short` in a required check if it skips tests.** That is a skipped test.
- `golangci-lint run --new-from-rev=BASE` reports only new issues. That is "checking less" when it is the only lint run: use it for fast PR feedback, and run the full lint in the merge queue.

## Parallelism

- `-p N` sets how many test binaries run at once; `-parallel N` sets how many `t.Parallel()` tests run inside one binary. Both default to `GOMAXPROCS`. Match them to the runner's cores.

## Shards

gotestsum splits packages into shards from recorded times ([ci-matrix](https://github.com/gotestyourself/gotestsum/pull/258)):

```bash
go list ./... | gotestsum tool ci-matrix --partitions 4 --timing-files="timings/*.json"
gotestsum --jsonfile timings/run.json --packages="<shard packages>" -- -count=1
```

It splits packages, not tests: one slow package stays on the critical path, so split that package. Record the timing files from main's full runs. Prove the shards together cover `go list ./...`.

## Test selection

```bash
git diff --name-only BASE...HEAD
go list -json -deps -test ./...
```

Map changed files to packages, then add every package that imports them, including test imports (`TestImports`, `XTestImports`). `go.mod`, `go.sum`, generated code, embedded files, and CI config rerun everything ([go list](https://pkg.go.dev/cmd/go/internal/list)).

## Never in a required check

`gotestsum --rerun-fails`: a retry hides the bug.

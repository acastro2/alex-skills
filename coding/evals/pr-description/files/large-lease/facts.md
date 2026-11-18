# Facts for PR #341 (branch refactor/ingest-lease, base main)

Gathered by hand; each block is the real command and its output.

## $ git log --reverse --format='%h %s' main..HEAD
a1c3e5f refactor(ingest): extract BulkWriter from the worker loop
b2d4f60 feat(ingest): retry BulkWriter writes with jitter
c3e5a71 feat(lease): add LeaseStore with claim, renew, release
d4f6b82 refactor(worker): claim a lease per partition, release on failure
e5a7c93 test(ingest): golden fixtures for batch publish order
f6b8da4 chore(ingest): delete legacy bulk_loop.py

## $ git diff --name-status main HEAD -- src
M	src/ingest/worker.py
D	src/ingest/bulk_loop.py
A	src/ingest/bulk_writer.py
A	src/ingest/lease.py
M	src/ingest/publish.py

## $ git diff --shortstat main HEAD -- src
 5 files changed, 558 insertions(+), 1501 deletions(-)

## $ git diff --shortstat main HEAD -- tests ':!tests/fixtures'
 3 files changed, 644 insertions(+), 140 deletions(-)

## $ git diff --shortstat main HEAD -- tests/fixtures
 42 files changed, 6120 insertions(+)

## $ git diff --shortstat main HEAD
 50 files changed, 7322 insertions(+), 1641 deletions(-)

## Line counts (git show main:<path> | wc -l ; wc -l <path>)
| path | main | HEAD |
| --- | --- | --- |
| src/ingest/worker.py | 1312 | 418 |
| src/ingest/bulk_loop.py | 540 | deleted |
| src/ingest/bulk_writer.py | (new) | 286 |
| src/ingest/lease.py | (new) | 197 |
| src/ingest/publish.py | 233 | 241 |

## $ grep -n "^class \|    def " src/ingest/bulk_writer.py src/ingest/lease.py
src/ingest/bulk_writer.py:14:class BulkWriter:
src/ingest/bulk_writer.py:31:    def __init__(self, sink, *, max_attempts=3, base_delay=0.2, max_delay=5.0):
src/ingest/bulk_writer.py:48:    def write(self, batch) -> WriteResult:
src/ingest/bulk_writer.py:97:    def _attempt(self, batch, attempt):
src/ingest/lease.py:12:class LeaseHeld(Exception):
src/ingest/lease.py:18:class LeaseStore:
src/ingest/lease.py:25:    def __init__(self, conn, *, ttl_s=30, renew_every_s=10):
src/ingest/lease.py:39:    def claim(self, partition, owner) -> Lease:
src/ingest/lease.py:71:    def renew(self, lease) -> Lease:
src/ingest/lease.py:96:    def release(self, lease) -> None:

## How main worked (read from main:src/ingest/worker.py and bulk_loop.py)
- worker.py ran its own loop per partition and called bulk_loop.run_bulk(batch) directly.
- run_bulk had no retry: one sink error raised out and failed the whole run.
- Nothing stopped two workers from taking the same partition. INC-4471 (2026-09-18): two workers wrote partition 7 twice, 18,400 duplicate rows.
- publish.py was called from inside run_bulk, so a failed write could leave a half-published batch.

## How HEAD works (read from HEAD)
- worker.process_partition(p): lease = leases.claim(p, owner) -> for each batch: writer.write(batch) -> publish.publish(result) -> leases.renew(lease) every 10 s -> leases.release(lease) in finally.
- claim raises LeaseHeld if another owner holds an unexpired lease; the worker skips the partition and picks the next one.
- BulkWriter.write tries up to 3 attempts, delay min(5.0, 0.2 * 2**n) plus full jitter. After the last failure it returns WriteResult(ok=False) and the worker releases the lease and marks the batch failed. No publish for a failed batch.
- publish.py now takes a WriteResult and publishes only ok results (+14 -6 lines).

## Spec: ADR-0031 "Partition leases for ingest workers" (accepted 2026-10-02)
Intended behaviour changes:
1. A worker claims a lease on a partition before it writes. A second worker on the same partition skips it instead of double-writing.
2. A failed write is retried up to 3 times with jitter (base 200 ms, cap 5 s) before the batch fails. Before, one error failed the whole run.
3. A failed batch is never published. Before, a failed write could leave a half-published batch.
4. Lease TTL is 30 s, renewed every 10 s. A crashed worker's partition is free again after at most 30 s.
Must not change: the record schema, the publish topic names, the CLI flags of `ingest run`.
ADR said: use a Postgres advisory lock.
Implemented instead: a row in a `leases` table with `expires_at`, because the connection pool uses pgbouncer in transaction mode and advisory locks do not survive across transactions there.
Known gap: no test covers clock skew between workers larger than 2 s.

## $ pytest tests/ingest --co -q   (per file, HEAD)
tests/ingest/test_bulk_writer.py: 38 tests
tests/ingest/test_lease.py: 27 tests
tests/ingest/test_worker.py: 51 tests
(main: test_worker.py had 63 tests; test_bulk_writer.py and test_lease.py did not exist)

## $ pytest -q   (full suite)
HEAD: 412 passed, 1 skipped in 48.21s
main: 359 passed, 1 skipped in 41.07s
The 1 skipped test is tests/ingest/test_lease.py::test_claim_under_real_pgbouncer (needs a live pgbouncer; skipped in CI).

## Golden replay (scripts/replay_golden.py, run on main and on HEAD, outputs diffed)
42 golden batches replayed.
Published records byte-identical: 42 of 42.
Publish order identical: 41 of 42. batch_017 differs: on main it published a half batch before the sink error; on HEAD it publishes nothing for the failed attempt and the full batch on retry 2 (intended, change 3).

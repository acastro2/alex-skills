# Facts for PR #318 (branch fix/sync-retry-503, base main)

Ticket SYNC-212: "Nightly device sync fails the whole run when the upstream API returns one transient 503. Three failed runs in October, each needed a manual rerun."

## $ git log --reverse --format='%h %s' main..HEAD
7a91c2e fix(sync): retry fetch_page on 502/503/504 with backoff
3be04d1 test(sync): cover retry exhaustion and non-retryable 404

## $ git diff --shortstat main HEAD -- src
 1 file changed, 14 insertions(+), 4 deletions(-)

## $ git diff --shortstat main HEAD -- tests
 1 file changed, 41 insertions(+)

## $ git show main:src/sync/client.py | wc -l ; wc -l src/sync/client.py
     118
     128 src/sync/client.py

## $ pytest tests/sync -q
......                                                                   [100%]
6 passed in 0.84s

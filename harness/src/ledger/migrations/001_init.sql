-- Harness ledger, first migration. Source: docs/specs/harness-ledger.erd.json (17 tables, D83 to D87).
-- ULID TEXT keys, INTEGER keys on journal/processes/snapshots, Unix-ms INTEGER times.
-- Every foreign key that points at journal uses ON DELETE SET NULL (D87), so a prune never cascades.

CREATE TABLE schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE sessions (
  id                TEXT PRIMARY KEY,
  parent_session_id TEXT REFERENCES sessions(id),
  tool              TEXT NOT NULL,
  repo              TEXT,
  cwd               TEXT,
  model             TEXT,
  interactive       INTEGER,
  started_at        INTEGER NOT NULL,
  ended_at          INTEGER
);

CREATE TABLE rules (
  id           TEXT PRIMARY KEY,
  event        TEXT NOT NULL,
  module       TEXT NOT NULL,
  mode         TEXT NOT NULL CHECK (mode IN ('enforce', 'advise', 'inject', 'off')),
  default_mode TEXT NOT NULL CHECK (default_mode IN ('enforce', 'advise', 'inject', 'off')),
  ships_in     TEXT,
  wrong_today  INTEGER NOT NULL DEFAULT 0,
  updated_at   INTEGER
);

CREATE TABLE journal (
  seq         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT REFERENCES sessions(id),
  turn        INTEGER,
  time        INTEGER NOT NULL,
  event       TEXT NOT NULL,
  rule_id     TEXT REFERENCES rules(id),
  outcome     TEXT,
  reason      TEXT,
  prompt_text TEXT,
  args_hash   TEXT,
  output_hash TEXT,
  data_json   TEXT CHECK (json_valid(data_json)),
  prev_hash   TEXT NOT NULL,
  row_hash    TEXT NOT NULL UNIQUE
);

CREATE TABLE requests (
  id         TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  sha        TEXT NOT NULL,
  digest     TEXT NOT NULL,
  review_seq INTEGER REFERENCES journal(seq) ON DELETE SET NULL,
  state      TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE tokens (
  id         TEXT PRIMARY KEY,
  kind       TEXT NOT NULL CHECK (kind IN ('merge', 'harness')),
  session_id TEXT REFERENCES sessions(id),
  grant_seq  INTEGER REFERENCES journal(seq) ON DELETE SET NULL,
  request_id TEXT REFERENCES requests(id),
  pr         INTEGER,
  expires_at INTEGER NOT NULL,
  used_at    INTEGER
);

CREATE TABLE applies (
  id             TEXT PRIMARY KEY,
  request_id     TEXT REFERENCES requests(id),
  token_id       TEXT NOT NULL REFERENCES tokens(id),
  sha            TEXT,
  tree_hash      TEXT,
  schema_version INTEGER,
  applied_at     INTEGER,
  rolled_back_at INTEGER
);

CREATE TABLE page_auth (
  credential_id TEXT PRIMARY KEY,
  public_key    BLOB,
  sign_count    INTEGER,
  session_until INTEGER
);

CREATE TABLE processes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  TEXT REFERENCES sessions(id),
  pid         INTEGER,
  command     TEXT,
  port        INTEGER,
  keep        INTEGER,
  started_at  INTEGER,
  ended_at    INTEGER,
  reported_at INTEGER
);

CREATE TABLE snapshots (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT REFERENCES sessions(id),
  state_json TEXT CHECK (json_valid(state_json)),
  created_at INTEGER
);

CREATE TABLE workstreams (
  id               TEXT PRIMARY KEY,
  owner_session_id TEXT REFERENCES sessions(id),
  repo             TEXT,
  title            TEXT,
  state            TEXT,
  updated_at       INTEGER
);

CREATE TABLE workers (
  id                TEXT PRIMARY KEY,
  parent_session_id TEXT REFERENCES sessions(id),
  worker_session_id TEXT REFERENCES sessions(id),
  worktree_id       TEXT REFERENCES worktrees(id),
  model             TEXT,
  base_sha          TEXT,
  test_hashes       TEXT,
  acceptance        TEXT,
  ladder_round      INTEGER,
  last_activity     INTEGER
);

CREATE TABLE bundles (
  id            TEXT PRIMARY KEY,
  worker_id     TEXT REFERENCES workers(id),
  session_id    TEXT REFERENCES sessions(id),
  journal_seq   INTEGER REFERENCES journal(seq) ON DELETE SET NULL,
  head_sha      TEXT,
  did_json      TEXT CHECK (json_valid(did_json)),
  works_json    TEXT CHECK (json_valid(works_json)),
  verified_json TEXT CHECK (json_valid(verified_json)),
  verdict       TEXT,
  advisory      REAL,
  summary       TEXT,
  known_gaps    TEXT
);

CREATE TABLE worktrees (
  id                TEXT PRIMARY KEY,
  workstream_id     TEXT REFERENCES workstreams(id),
  session_id        TEXT REFERENCES sessions(id),
  landed_bundle_id  TEXT REFERENCES bundles(id),
  repo              TEXT,
  path              TEXT UNIQUE,
  branch            TEXT,
  state             TEXT,
  sync_state        TEXT,
  conflict_files    TEXT,
  synced_at         INTEGER,
  created_at        INTEGER,
  removed_at        INTEGER
);

CREATE TABLE watches (
  id         TEXT PRIMARY KEY,
  session_id TEXT REFERENCES sessions(id),
  worker_id  TEXT REFERENCES workers(id),
  kind       TEXT,
  target     TEXT,
  last_state TEXT,
  polled_at  INTEGER,
  expires_at INTEGER
);

CREATE TABLE jobs (
  name        TEXT PRIMARY KEY,
  schedule    TEXT,
  last_run_at INTEGER,
  last_result TEXT,
  last_seq    INTEGER REFERENCES journal(seq) ON DELETE SET NULL
);

CREATE TABLE workstream_steps (
  id            TEXT PRIMARY KEY,
  workstream_id TEXT NOT NULL REFERENCES workstreams(id),
  position      INTEGER,
  text          TEXT,
  state         TEXT,
  bundle_id     TEXT REFERENCES bundles(id),
  done_at       INTEGER
);

-- Projections over the journal (D85). Extra fields live in data_json.
CREATE VIEW sendbacks AS
  SELECT seq, session_id, turn, time, rule_id, outcome, reason, data_json
  FROM journal WHERE event = 'stop.sendback';

CREATE VIEW nudges AS
  SELECT seq, session_id, turn, time, rule_id, outcome, reason, data_json
  FROM journal WHERE event = 'nudge';

CREATE VIEW corrections AS
  SELECT seq, session_id, turn, time, rule_id, prompt_text, data_json
  FROM journal WHERE event = 'correction';

CREATE VIEW egress AS
  SELECT seq, session_id, turn, time, rule_id, reason, data_json
  FROM journal WHERE event = 'egress.warning';

CREATE INDEX journal_session_seq ON journal(session_id, seq);
CREATE INDEX journal_rule_time   ON journal(rule_id, time);
CREATE INDEX journal_event_time  ON journal(event, time);
CREATE INDEX worktrees_repo_state ON worktrees(repo, state);
CREATE INDEX watches_expires     ON watches(expires_at);

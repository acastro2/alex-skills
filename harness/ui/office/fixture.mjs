// Demo fixture: a LedgerSnapshot and the changes the demo button cycles through.
// Runs in the page (inlined by build.mjs). `officeState` comes from office-model.ts.

const MIN = 60_000;

export function baseSnapshot(now) {
  const s = (id, extra) => ({ id, tool: "opencode", parent_session_id: null, repo: "skills", goal: null, running: false, stuck: false, waitingQuestion: false, started_at: now - 90 * MIN, ended_at: null, last_activity: now - 4 * MIN, ...extra });
  return {
    now,
    host: "vm-01",
    harnessOff: false,
    sessions: [
      s("ses_alpha1", { goal: "Refactor the ledger migrations", running: true, last_activity: now - 6_000, repo: "harness" }),
      s("ses_beta22", { goal: "Which retry policy for the waker?", waitingQuestion: true, tool: "claude", last_activity: now - 7 * MIN, repo: "harness" }),
      s("ses_gamma3", { goal: "Upgrade Terraform providers", running: true, last_activity: now - 20_000, repo: "infra" }),
      s("ses_delta4", { goal: "Fix flaky shell parser test", stuck: true, last_activity: now - 18 * MIN, repo: "harness" }),
      s("ses_work01", { goal: "Write shell rule tests", running: true, parent_session_id: "ses_alpha1", last_activity: now - 3_000, repo: "harness" }),
      s("ses_work02", { goal: "Plan the module graph", parent_session_id: "ses_gamma3", last_activity: now - 90_000, repo: "infra", tool: "claude" }),
    ],
    worktrees: [
      { id: "wt1", repo: "harness", branch: "feat/ledger", state: "active", sync_state: "current", session_id: "ses_alpha1" },
      { id: "wt2", repo: "infra", branch: "chore/tf-upgrade", state: "active", sync_state: "behind", session_id: "ses_gamma3" },
      { id: "wt3", repo: "harness", branch: "fix/parser", state: "active", sync_state: "conflict", session_id: "ses_delta4" },
      { id: "wt4", repo: "skills", branch: "docs/office", state: "held", sync_state: "current", session_id: null },
    ],
    wakes: [
      { session_id: "ses_alpha1", kind: "scheduled", time: now - 700 },
      { session_id: "ses_gamma3", kind: "scheduled", time: now - 1_500 },
    ],
    journalRate: 24,
    denies: 2,
    grants: [{ id: "g1", time: now - 6 * MIN, used_at: null }],
    steeringShare: 0.31,
    jobs: [
      { name: "gather", next_at: now + 25 * MIN },
      { name: "bard sweep", next_at: now + 3 * 3_600_000 },
    ],
    rules: [
      { id: "shell.rm", mode: "enforce" },
      { id: "git.push", mode: "enforce" },
      { id: "path.etc", mode: "enforce" },
      { id: "proof.done", mode: "advise" },
      { id: "link.pr", mode: "inject" },
      { id: "voice", mode: "off" },
    ],
    bell: false,
  };
}

const extra = (now, n) => Array.from({ length: n }, (_, i) => ({ id: `ses_more${i}`, tool: "opencode", parent_session_id: null, repo: "skills", goal: `Background task ${i + 1}`, running: i % 2 === 0, stuck: false, waitingQuestion: false, started_at: now - 40 * MIN, ended_at: null, last_activity: now - (i + 1) * 40_000 }));

export const CHANGES = [
  { name: "Answer the question", apply: (s) => ({ ...s, sessions: s.sessions.map((x) => (x.id === "ses_beta22" ? { ...x, waitingQuestion: false, running: true, last_activity: s.now } : x)), wakes: [{ session_id: "ses_beta22", kind: "answer", time: s.now - 200 }] }) },
  { name: "Journal burst and a grant", apply: (s) => ({ ...s, journalRate: 640, denies: 5, steeringShare: 0.12, grants: [{ id: "g2", time: s.now, used_at: null }, { id: "g3", time: s.now, used_at: null }], wakes: [] }) },
  { name: "Add four more sessions", apply: (s) => ({ ...s, sessions: [...s.sessions, ...extra(s.now, 4)], journalRate: 90, wakes: [] }) },
  { name: "Rack overflows, question on the rack", apply: (s) => ({ ...s, sessions: [...s.sessions.map((x) => x), ...extra(s.now, 3).map((x, i) => ({ ...x, id: `ses_late${i}`, waitingQuestion: i === 2, last_activity: s.now - 1_000 }))], wakes: [] }) },
  { name: "Ring the bell, switch the harness off", apply: (s) => ({ ...s, bell: true, harnessOff: true, wakes: [] }) },
  { name: "Land the conflict", apply: (s) => ({ ...s, bell: false, harnessOff: false, worktrees: s.worktrees.map((w) => (w.id === "wt3" ? { ...w, state: "removed", sync_state: null } : w)), wakes: [] }) },
  { name: "Empty floor", apply: (s) => ({ ...s, sessions: [], worktrees: [], wakes: [], journalRate: 0, denies: 0, grants: [], steeringShare: null, jobs: [], bell: false }) },
];

/** Snapshot after `step` changes, applied one on top of the other. */
export function fixtureAt(step, now) {
  let snap = baseSnapshot(now);
  for (let i = 0; i < step; i++) snap = CHANGES[i % CHANGES.length].apply(snap);
  return { ...snap, now };
}

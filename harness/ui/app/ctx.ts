// Shared types and the small UI state that survives a re-render.
import type { Snapshot, ViewId } from "../../src/serve/snapshot.ts";

export type { Snapshot, ViewId };
export type {
  BundleRow,
  ChangeRow,
  CommandRun,
  JobRow,
  JournalPage,
  JournalRow,
  PrWatchRow,
  ProcessRow,
  QuestionRow,
  RuleRow,
  SessionRow,
  TailKind,
  TailRow,
  ToolCall,
  WorktreeRow,
} from "../../src/serve/snapshot.ts";

export type { ProcSample, ResourcePoint, Resources, Tone as MachineTone } from "../../src/serve/resources.ts";

/** The 8 ledger views, plus "machine": it reads `snap.resources`, so it has no row in the counts and alerts records. */
export type UiViewId = ViewId | "machine";

export const VIEWS: { id: UiViewId; label: string; short: string; blurb: string }[] = [
  { id: "inbox", short: "Inbox", label: "Inbox", blurb: "Questions waiting for you, oldest first." },
  { id: "sessions", short: "Sessions", label: "Sessions and workers", blurb: "Every live session, what it is doing, and its workers." },
  { id: "worktrees", short: "Worktrees", label: "Worktrees and conflicts", blurb: "Each worktree, who owns it, and whether it is in sync." },
  { id: "bundles", short: "Proof bundles", label: "Proof bundles", blurb: "What the harness re-ran, next to what the worker claimed." },
  { id: "rules", short: "Rules", label: "Rules", blurb: "Each rule, its mode, and the send-backs it made today." },
  { id: "journal", short: "Journal", label: "Journal and replay", blurb: "The ledger's journal, paged. Replay one session step by step." },
  { id: "changes", short: "Changes", label: "Harness changes", blurb: "Changes to the harness itself, waiting for your tap." },
  { id: "jobs", short: "Jobs", label: "Jobs", blurb: "Scheduled jobs: last run, result, next run." },
  { id: "machine", short: "Machine", label: "Machine", blurb: "How hard this machine is working: CPU, memory, disk, pressure, top processes." },
];

/** "office" is the route of the dashboard (the home page, #/ and #/office). The 8 views are its drill-down pages. */
export type ViewName = "office" | UiViewId;

export interface Route {
  view: ViewName;
  id: string | null;
  q: Record<string, string>;
}

export interface JournalUi {
  filters: { session: string; rule: string; event: string; q: string; since: string };
  rows: import("../../src/serve/snapshot.ts").JournalRow[];
  hasMore: boolean;
  next: number | null;
  loading: boolean;
  error: string | null;
  topSeq: number;
  key: string;
  routeSig: string;
  replay: { session: string; rows: import("../../src/serve/snapshot.ts").JournalRow[]; index: number; hasMore: boolean; loading: boolean; error: string | null } | null;
}

export interface UiState {
  expanded: Set<string>;
  drafts: Map<string, string>;
  pending: Set<string>;
  sent: Set<string>;
  journal: JournalUi;
  /** Set by the journal view: called on every snapshot so it can update its "new rows" bar in place. */
  pulse: ((snap: Snapshot) => void) | null;
}

export interface Ctx {
  snap: Snapshot;
  route: Route;
  now: number;
  ui: UiState;
  go(hash: string): void;
  /** Run an action, show the outcome in the status line, and return true when it worked. */
  act(key: string, action: string, args: Record<string, unknown>, done: string): Promise<boolean>;
  rerender(): void;
  toggle(key: string): void;
}

export const viewLabel = (id: ViewName) => (id === "office" ? "Dashboard" : VIEWS.find((v) => v.id === id)?.label ?? id);

export function parseHash(hash: string): Route {
  const raw = hash.replace(/^#\/?/, "");
  const [path, query = ""] = raw.split("?");
  const [view, ...rest] = path.split("/").filter(Boolean);
  const q: Record<string, string> = {};
  for (const [k, v] of new URLSearchParams(query)) q[k] = v;
  const known = view === "office" || VIEWS.some((v) => v.id === view);
  return { view: known ? (view as ViewName) : "office", id: rest.length ? decodeURIComponent(rest.join("/")) : null, q };
}

export function hashFor(view: ViewName, id?: string | null, q?: Record<string, string>): string {
  const query = q && Object.keys(q).length ? `?${new URLSearchParams(q)}` : "";
  return `#/${view}${id ? `/${encodeURIComponent(id)}` : ""}${query}`;
}

// O11: a silent browser notification when a question arrives or a session goes stuck.
// Permission is asked only from the top-bar button, never on page load.
import type { Snapshot } from "./ctx.ts";

const seenQuestions = new Set<number>();
const stuckSessions = new Set<string>();
let primed = false;

export const supported = () => "Notification" in window;
export const permission = (): NotificationPermission | "unsupported" => (supported() ? Notification.permission : "unsupported");

export async function askPermission(): Promise<NotificationPermission | "unsupported"> {
  if (!supported()) return "unsupported";
  return Notification.requestPermission();
}

/** Call with each snapshot. The first call only records what is already there. */
export function notifyChanges(snap: Snapshot, onOpen: (hash: string) => void): void {
  const questions = snap.views.inbox;
  const stuck = snap.views.sessions.filter((s) => s.stuck);
  const fresh: { title: string; body: string; tag: string; hash: string }[] = [];
  for (const q of questions) {
    if (!seenQuestions.has(q.seq)) {
      seenQuestions.add(q.seq);
      fresh.push({ title: `${q.session_slug} asks`, body: q.text.slice(0, 140), tag: `q-${q.seq}`, hash: `#/inbox/${q.seq}` });
    }
  }
  for (const s of stuck) {
    if (!stuckSessions.has(s.id)) {
      stuckSessions.add(s.id);
      fresh.push({ title: `${s.slug} is stuck`, body: s.goal ?? "No goal recorded", tag: `s-${s.id}`, hash: `#/sessions/${s.id}` });
    }
  }
  for (const id of [...stuckSessions]) if (!stuck.some((s) => s.id === id)) stuckSessions.delete(id);

  if (!primed) {
    primed = true;
    return;
  }
  if (permission() !== "granted") return;
  for (const f of fresh) {
    const n = new Notification(f.title, { body: f.body, tag: f.tag, silent: true });
    n.onclick = () => {
      window.focus();
      onOpen(f.hash);
      n.close();
    };
  }
}

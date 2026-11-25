import { h } from "../dom.ts";
import type { Ctx, QuestionRow } from "../ctx.ts";
import { hashFor } from "../ctx.ts";
import { timeEl } from "../dom.ts";
import { btn, empty, sessionLink, viewHeader } from "../parts.ts";

function question(ctx: Ctx, q: QuestionRow): HTMLElement {
  const key = `answer:${q.seq}`;
  const sent = ctx.ui.sent.has(key);
  const busy = ctx.ui.pending.has(key);
  const selected = ctx.route.id === String(q.seq) || ctx.route.id === q.session_id;
  const draft = ctx.ui.drafts.get(key) ?? "";
  const send = (text: string) => {
    if (!text.trim()) return;
    void ctx.act(key, "answer", { session_id: q.session_id, seq: q.seq, text }, "Answer sent. The session gets it as its next prompt.").then((ok) => {
      if (ok) {
        ctx.ui.sent.add(key);
        ctx.ui.drafts.delete(key);
        ctx.rerender();
      }
    });
  };
  const area = h("textarea", {
    id: `answer-${q.seq}`,
    class: "field",
    rows: "2",
    placeholder: "Or write your own answer",
    disabled: sent || busy,
    onInput: (e: Event) => ctx.ui.drafts.set(key, (e.target as HTMLTextAreaElement).value),
    onKeydown: (e: KeyboardEvent) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send((e.target as HTMLTextAreaElement).value);
    },
  });
  area.value = draft;

  return h(
    "article",
    { class: `ask${selected ? " selected" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
    h(
      "div",
      { class: "ask-meta" },
      sessionLink(ctx, q.session_slug, q.session_id),
      h("span", { class: "dim" }, `${q.tool ?? "unknown tool"} · asked `),
      timeEl(q.asked_at, ctx.now),
    ),
    q.goal ? h("p", { class: "ask-goal" }, `Goal: ${q.goal}`) : null,
    h("p", { class: "ask-text" }, q.text || "The session asked a question with no text."),
    sent
      ? h("p", { class: "ask-sent" }, "Sent. This disappears when the session picks it up.")
      : h(
          "div",
          { class: "ask-answer" },
          q.options.length
            ? h(
                "div",
                { class: "options", role: "group", "aria-label": "Options" },
                q.options.map((o) => btn(o, { busy, onClick: () => send(o) })),
              )
            : null,
          h("label", { class: "sr", for: `answer-${q.seq}` }, "Your answer"),
          area,
          h(
            "div",
            { class: "ask-actions" },
            btn("Send answer", { tone: "primary", busy, onClick: () => send(area.value) }),
            h("span", { class: "hint" }, "An answer is only text for the session. It never grants a merge."),
            h("a", { class: "link", href: hashFor("journal", null, { session: q.session_id }) }, "Open journal"),
          ),
        ),
  );
}

export function renderInbox(ctx: Ctx): HTMLElement {
  const qs = ctx.snap.views.inbox;
  return h(
    "section",
    { class: "view", "aria-labelledby": "view-h" },
    viewHeader(ctx, "inbox"),
    qs.length
      ? h("div", { class: "asks" }, qs.map((q) => question(ctx, q)))
      : empty("No questions waiting.", "A question shows here when a session asks you something and stops to wait."),
  );
}

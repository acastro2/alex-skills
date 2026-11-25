import { h, timeEl } from "../dom.ts";
import type { Ctx, RuleRow } from "../ctx.ts";
import { btn, chip, dataTable, detailRow, empty, expandToggle, sessionLink, td, viewHeader, type Tone } from "../parts.ts";

const MODE_TONE: Record<string, Tone> = { enforce: "ink", advise: "neutral", inject: "neutral", off: "red" };

function modeCell(r: RuleRow) {
  const changed = r.default_mode && r.default_mode !== r.mode;
  return h("span", null, chip(MODE_TONE[r.mode] ?? "neutral", r.mode), changed ? h("span", { class: "dim block" }, `default ${r.default_mode}`) : null);
}

export function renderRules(ctx: Ctx): HTMLElement {
  const rules = ctx.snap.views.rules;
  const body: HTMLElement[] = [];
  const cols = 7;
  for (const r of rules) {
    const key = `rule:${r.id}`;
    const selected = ctx.route.id === r.id;
    const open = ctx.ui.expanded.has(key) || selected;
    const onKey = `on:${r.id}`;
    body.push(
      h(
        "tr",
        { class: `${selected ? "selected" : ""}${open ? " is-open" : ""}`, "data-selected": selected ? "true" : undefined, "aria-current": selected ? "true" : undefined },
        td("Rule", "c-session", expandToggle(ctx, key, r.id, open, h("span", { class: "mono strong" }, r.id))),
        td("Module", null, r.module ?? "", h("span", { class: "dim mono block" }, r.event ?? "")),
        td("Mode", null, modeCell(r)),
        td("Ships in", null, r.ships_in ?? h("span", { class: "dim" }, "unknown")),
        td("Send-backs today", "num", r.sendbacks_today ? String(r.sendbacks_today) : h("span", { class: "dim" }, "0")),
        td("Wrong today", "num", r.wrong_today ? h("span", { class: "warn-text" }, String(r.wrong_today)) : h("span", { class: "dim" }, "0")),
        td("", "c-act", r.mode === "off" ? btn("Turn on", { busy: ctx.ui.pending.has(onKey), title: "Needs a passkey tap", icon: "key", onClick: () => void ctx.act(onKey, "on", { rule: r.id }, `Rule ${r.id} is on.`) }) : null),
      ),
    );
    if (open) {
      body.push(
        detailRow(
          cols,
          h("h3", null, "Send-backs today"),
          r.recent_sendbacks.length
            ? h(
                "ul",
                { class: "sendbacks" },
                r.recent_sendbacks.map((s) => {
                  const wkey = `wrong:${s.seq}`;
                  return h(
                    "li",
                    null,
                    h("div", { class: "sb-meta" }, h("span", { class: "mono dim" }, `#${s.seq}`), sessionLink(ctx, s.session_slug, s.session_id), timeEl(s.time, ctx.now)),
                    h("p", { class: "sb-reason" }, s.reason ?? "No reason recorded."),
                    s.wrong || ctx.ui.sent.has(wkey)
                      ? chip("amber", "marked wrong")
                      : btn("Mark wrong", { busy: ctx.ui.pending.has(wkey), title: "The send-back was a mistake", onClick: () => void ctx.act(wkey, "wrong", { seq: s.seq }, "Marked wrong. It counts against this rule today.").then((ok) => ok && ctx.ui.sent.add(wkey)) }),
                  );
                }),
              )
            : h("p", { class: "dim" }, "No send-backs from this rule today."),
        ),
      );
    }
  }
  return h(
    "section",
    { class: "view" },
    viewHeader(ctx, "rules"),
    rules.length
      ? dataTable(
          [{ label: "Rule" }, { label: "Module" }, { label: "Mode" }, { label: "Ships in" }, { label: "Send-backs today", cls: "num" }, { label: "Wrong today", cls: "num" }, { label: "Actions", cls: "c-act" }],
          body,
          "Rules",
        )
      : empty("No rules loaded.", "Rules show here once the harness is installed and has read its manifest."),
  );
}

---
name: comms-writer
description: Generates ready-to-send emails and Microsoft Teams messages in the Attain house voice. Use when you need to communicate clearly and effectively with team members, stakeholders, or leadership. It focuses on clarity, brevity, and a conversational yet professional tone.
---

# Comms Writer

## When to use this skill

Use this skill when you need help drafting:

- **Team Updates** (Teams/Email)
- **Stakeholder Communications** (Teams/Email)
- **Leadership Updates** (Email)
- **Meeting Requests/Agendas** (Teams/Email)
- **General Announcements** (Teams/Email)
- **Feedback** (Teams/Email)

Do NOT use this for:

- Formal documentation (Use `docs-writer` skill)
- Blog posts (Use `blog-writer` task)
- Code reviews (Use `pr-reviewer` skill)
- Formal internal 3P/newsletter comms (Use `internal-comms` skill unless instructed otherwise)

## How to use this skill

Follow this interactive workflow:

1. **Understand the Request**:
    - Ask the user for **Context**: "What is the core message? Who is the audience? What are the key points?"
    - Ask the user for **Format**: "Is this an Email or a Teams message?"
    - If the user provided this information upfront, skip the questions.

2. **Generate the Draft**:
    - Consult the shared voice files referenced below for tone and style guidelines.
    - Draft the communication.
    - Ensure it is **copy-paste ready** (subject lines included for email).

3. **Refine**:
    - Ask the user if the draft captures the intent.
    - Offer to tweak tone or length if needed.

## Voice & Tone

This skill adheres strictly to the Attain house voice: conversational, direct, substantial, and warm.

> **Voice Reference:** Before drafting, read the shared voice files:
>
> - `shared/attain-voice-core.md` — Personality, principles, signature phrases, anti-patterns
> - `shared/attain-voice-comms.md` — Email/Teams calibration and structure

## Communication Types & Examples

### Teams Updates

- **Goal**: Quick, skimmable, action-oriented.
- **Structure**:
  - **Headline**: Bolded summary.
  - **Context**: 1-2 sentences.
  - **Details**: Bullets if needed.
  - **CTA**: Clear next step or "FYI".

#### Teams Formatting — HTML File Approach (CRITICAL)

Teams' compose box is a rich-text editor, just like Slack and Outlook. Pasting raw markdown gives literal `**asterisks**` and `_underscores_` — the markdown shortcuts only render when typed live into the box. Anything pasted from a code block or terminal arrives mangled.

The reliable workaround: **generate an HTML file, have the user open it in a browser, Cmd+A / Ctrl+A to select all, Cmd+C / Ctrl+C to copy, and paste into the Teams compose box.** Teams preserves rich text (bold, italic, lists, headings, links, code) from the browser clipboard with high fidelity.

**Always write Teams messages to `/tmp/<descriptive-name>.html`** and open it for the user:
```bash
open /tmp/<descriptive-name>.html   # macOS
xdg-open /tmp/<descriptive-name>.html  # Linux
```

Tell the user: "Open the file in your browser, Cmd+A to select all, Cmd+C to copy, paste into Teams."

**HTML rules — what Teams preserves (desktop + web):**

Teams uses an Edge-based rich-text editor and handles a much wider HTML surface than Slack. Unlike the Slack flow, you can use real lists, headings, and code blocks.

| HTML | Teams result | Use? |
|------|--------------|------|
| `<b>text</b>` / `<strong>` | **Bold** | Yes |
| `<i>text</i>` / `<em>` | *Italic* | Yes |
| `<u>text</u>` | Underline | Yes |
| `<s>text</s>` / `<del>` | Strikethrough | Yes |
| `<a href="...">` | Clickable link | Yes |
| `<br>` | Line break | Yes |
| `<p>` | Paragraph with spacing | Yes |
| `<ul><li>` / `<ol><li>` | Native bullets / numbered lists | Yes |
| `<h1>` – `<h3>` | Renders as Teams heading sizes | Yes (use sparingly) |
| `<blockquote>` | Vertical bar + indent quote block | Yes |
| `<pre><code>` | Monospace code block | Yes |
| `<code>` inline | Inline monospace | Yes |
| `<h4>`–`<h6>` | Flattened to bold paragraphs | Avoid — use `<h3>` or `<b>` |
| `<table>` | Inconsistent rendering, often flattens | Avoid for chats; OK in channel posts |
| Background colors / inline `style="color:..."` | Stripped | Don't rely on |

**Bullet lists are the big win over Slack** — use `<ul>` / `<ol>` natively. No more `&nbsp;&nbsp;•` workarounds.

**Code snippets:** wrap in `<pre><code>...</code></pre>`. Teams renders these as proper monospace blocks. For inline code, `<code>` works inside paragraphs.

**Mentions:** Plain HTML can't trigger a real `@mention` notification — Teams only does that for live-typed `@name` selections. If a notification matters, tell the user to type the @mention manually after pasting.

**Emoji:** use Unicode characters directly (✅ 🎯 💭). HTML entities (`&#x2705;`) also work. Teams renders these natively in the message body.

**Minimal HTML template (Teams-optimized):**
```html
<html>
<head>
<style>
  body { font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.5; max-width: 700px; margin: 40px auto; color: #242424; }
  h1, h2, h3 { margin: 1em 0 0.4em; }
  ul, ol { margin: 0.4em 0 0.8em 1.2em; padding-left: 1em; }
  li { margin: 0.15em 0; }
  blockquote { border-left: 3px solid #c7c7c7; margin: 0.6em 0; padding: 0.2em 0.8em; color: #424242; }
  pre { background: #f3f2f1; padding: 10px 12px; border-radius: 4px; font-family: Consolas, "Courier New", monospace; font-size: 13px; overflow-x: auto; }
  code { font-family: Consolas, "Courier New", monospace; background: #f3f2f1; padding: 1px 4px; border-radius: 3px; }
  pre code { background: none; padding: 0; }
  a { color: #0078d4; }
</style>
</head>
<body>
<!-- content here using <b>, <i>, <ul>, <h3>, <blockquote>, <pre><code>, etc. -->
</body>
</html>
```

**Quick gotchas:**
- Teams' compose box has a max length (~28KB for chat, larger for channel posts). For long updates, prefer a channel post or break into multiple messages.
- The "Format" button (the `A` icon in the compose box) opens an expanded editor — recommend it to the user when pasting longer messages so they can see the rendered result before sending.
- Channel posts support a Subject line; chats don't. If the draft is a channel post, surface a subject as the first `<h3>`.

### Email Updates

- **Goal**: Comprehensive but respectful of time.
- **Structure**:
  - **Subject**: Actionable. e.g., "[Update] Q3 Roadmap Status".
  - **Opening**: "Hi team," + Hook (Why this matters).
  - **Body**: Structured with clear headings or bullets.
  - **Closing**: "Thanks," + Name.

## Checklist for Every Draft

Before showing the draft to the user, verify:

- [ ] Does it sound human and on-voice?
- [ ] Are there any AI-isms ("It's worth noting", "delve into")? -> **REMOVE THEM**.
- [ ] Is the "Why" clear in the first 2 sentences?
- [ ] Is it formatted correctly for the medium (Subject line for email, bolding and structure for Teams)?
- [ ] Is it actionable?

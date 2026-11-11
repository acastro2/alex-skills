---
name: design-system
description: "Apply Alex's work design system (colors, type, shapes, status colors, do's and don'ts) from the DESIGN.md that a work repo owns. Use whenever you build or restyle anything visual for Alex's work: internal portals, docs sites, admin consoles, dashboards, Artifacts, HTML pages, slides, diagrams, or charts, even when the user does not say 'design system' or 'brand'. Not for Alex's personal projects or blog, and not for changing the design system itself; that is a PR on the repo that owns the file."
---

# Design system

## Asking

When you need a decision from Alex, ask through the `question` tool, not prose. One call
carries the whole round. The recommended option goes first, and its description carries the
why. Do not add a "type your own answer" option: the tool adds it. A decision with one
plausible answer is not a question, so decide it and say why. Where this skill defines its
own review or answer format, that format wins. If the host has no question tool, use
`❓ **Q1 - <title>**: ...` and `➡️ <answer and why>` in the same place.

This skill is a pointer. The design system lives in one `DESIGN.md`, owned by a work repo.
Where that file is lives in a private config, outside this repo:

```
~/.config/design-system.json
{
  "local": "<path to the DESIGN.md in a local clone>",
  "github_repo": "<owner>/<repo>",
  "github_path": "DESIGN.md"
}
```

Never copy the file, its values, or the names in the config into this repo. This repo is
public, and the file holds internal brand rules and staff names. A copy would also drift
from the source.

## Step 1: read the source

1. Read `~/.config/design-system.json`. If it is missing, stop and ask Alex for the repo.
2. Read the whole `local` file. It follows the Google DESIGN.md format: YAML tokens at the
   top, prose sections below.
3. If the local file is missing (another machine, a cloud session), read it from GitHub,
   read-only, with the config values:

   ```bash
   gh api "repos/<github_repo>/contents/<github_path>" -H "Accept: application/vnd.github.raw"
   ```

4. If both fail, stop and tell Alex. Do not build from memory: a guessed hex value is a
   brand error that looks correct.

The local clone can be behind the default branch. When the work ships to other people,
compare the local file with the GitHub copy and say which one you used.

## Step 2: apply it

- **Tokens are the rule.** Use the exact values from the YAML block. Every color must trace
  back to the palette.
- **Respect the source tags.** When the file tags values by source, the brand-guide values
  are binding. Values taken from one real build are a sane default, not a rule.
- **Silence means ask.** Where the file has no value, do not invent one as if it were brand.
  Pick a plain default, label it as yours, and tell Alex.
- **Read the conflict notes.** The file can record places where the brand minimum fails
  WCAG. Take the choice that passes WCAG AA, and say so.
- **Status colors mean status.** Use them for state only, never as decoration or as text on
  white.

## Step 3: fit the medium

| Medium | How to apply |
| --- | --- |
| HTML page or Artifact | Put the colors on `:root` as CSS variables named after the tokens. Use the font stacks the file gives. The Artifact page contract still comes from `artifact-design`; the design file wins only on color, type, and shape. |
| Chart | Use the palette from the design file instead of the placeholder palette in `dataviz`. Brand colors for series, status colors only for status. |
| Diagram (`archify`) | Neutrals and the primary brand color for structure, status colors only for state. |
| Slides | Neutrals carry the slide, the primary brand color marks the one point. Keep the restraint the file describes. |

## Step 4: check before you hand it over

- Every color in the output is in the palette (grep the hex values).
- Every shape rule in the file's do's and don'ts holds (corners, line caps, button shape).
- Body text is at or above the size floor in the file.
- Say which copy of `DESIGN.md` you used (local or GitHub) and any value you had to invent.

## Changing the design system

Edits go to `DESIGN.md` in the repo that owns it, through a PR there. Never patch values in
the output to "fix" the brand, and never edit them here.

---
name: attain-design-system
description: The Attain Finance brand and design system, and the hub that routes any Attain-branded deliverable to the right production skill. Use this whenever you produce something a person at Attain will see — a deck or slides, a Word or PDF document, a web page or UI component, a chart, a logo or icon, marketing copy — even if the request never says "Attain" or "brand", as long as the work is for Attain Finance. Read it before picking any color, font, or spacing value, and consult it to learn which sibling skill (pptx, docx, frontend-design, uncodixfy) to drive and what brand specifics to apply.
---

# Attain Finance Design System

This skill is the **hub** for all Attain-branded work. `DESIGN.md` (in this skill directory) is the full source of truth: palette, typography, the wedge motif, semantic tokens, dark mode, component conventions, charts, accessibility, and the PowerPoint `.thmx` workflow. Read it for any non-trivial decision.

The sibling skills in this plugin (`pptx`, `docx`, `frontend-design`, `uncodixfy`) handle *mechanics* — how to write a `.pptx`, a `.docx`, or quality web UI. They are deliberately generic and brand-agnostic. **This skill supplies the brand they're missing.** When you produce an Attain artifact, drive the right sibling skill for mechanics, then apply the specifics below. Don't accept a sibling skill's generic defaults (Arial, Linear/Stripe palettes, stock chart colors) for Attain work.

## The brand in one screen

- **Palette:** Venice Blue `#094682` (primary — headings, primary buttons, wordmark), Curious Blue `#1D96D3` (accent — links, focus, hover), Kashmir Blue `#51779D` (muted — secondary text, dividers, table headers), Matisse `#197C98` (secondary CTAs, charts, info), Twill Brown `#DFD3B8` (warm neutral — backgrounds, callouts; **never body text**).
- **Type:** ITC Avant Garde Gothic Pro (display/headings; fallback Century Gothic) · Inter (web body) · Century Gothic (document/deck body — already in the `.thmx` theme) · JetBrains Mono (code, IDs, monetary fixed-width). Weights only: Avant Garde 400/500/700, Inter 400/500/600/700. No thin, no black.
- **Signature motif:** the diagonal **wedge** composition. Lean into angled hero sections, diagonal section breaks, triangular accents. Avoid pure flat rectangles for primary brand surfaces — they read off-brand.

## Producing an Attain artifact — route through the right skill

### Web page / UI component / dashboard / artifact
Drive **`frontend-design`** (quality direction) and **`uncodixfy`** (avoid generic-AI patterns), but:
- Swap their generic / Linear-Stripe-Raycast palette for the **Attain tokens** above.
- Set fonts to `--font-display` (Avant Garde → Century Gothic) for headings, **Inter** for body, **JetBrains Mono** for code/IDs/money. See DESIGN.md §3 for the CSS variables.
- Use the **wedge motif** for hero/brand surfaces.
- `uncodixfy`'s anti-bloat discipline still fully applies — the Attain palette changes *colors*, not its layout restraint.

### PowerPoint deck / slides
Drive **`pptx`** for mechanics, but **discard its generic palettes**. Instead:
- **If `assets/attain-theme.thmx` and `assets/attain-crystal.*` are present in this skill**, start from them. They are **not bundled by default** — see `assets/README.md`. Without them, reproduce the master in-script from the specs below and DESIGN.md §9 (the eval agents did this successfully), and substitute a small Venice-Blue wedge for the crystal mark.
- Slide size 13.33"×7.5" (16:9). **Type directly into placeholders** — pasting from external sources strips the theme's font/size/color.
- Body = **Century Gothic**; headings = Avant Garde where available.
- Keep the page number + crystal mark bottom-right on every content slide. Covers use the wedge composition, not stock photography (unless using the Photo Page layout).
- Pick the right master: **Standard** vs **Confidential & Proprietary** (every slide carries the C&P mark for non-public external decks).

### Word / PDF document
Drive **`docx`** for mechanics, but **override its Arial default**:
- Document font = **Century Gothic** (the brand document face); headings in Avant Garde where the device has it.
- Headings in Venice Blue; table headers in Kashmir Blue.
- On PDF export, **embed fonts** — Avant Garde Gothic Pro is licensed and will substitute (breaking the brand) if the export device lacks it.

### Chart / data viz
Primary blues first (Venice → Curious → Matisse), then the secondary **mid-row** palette only when you need more series (DESIGN.md §6). Never repurpose status colors for decorative data.

### Documenting a *different* (non-Attain) design system
**`design-md`** generates a DESIGN.md from a Stitch project — that's for capturing *another* project's system, not for applying Attain's. Don't use it to style Attain work.

## Read `DESIGN.md` before
Picking colors/fonts/spacing · styling UI · authoring marketing pages or hero sections · producing PowerPoint/Word/PDF · choosing chart palettes · designing logos/icons/imagery. Treat its rules as binding unless explicitly told otherwise.

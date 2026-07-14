# Attain Finance — Design System

> **Tagline:** *Helping People Attain What Matters*
> Single source of truth for visual language across web apps, marketing site, internal tools, and documents/decks. Pulled from the Attain Finance 2025 brand guidelines and PowerPoint template.

---

## 1. Brand Foundation

### 1.1 Voice & character

Confident, trustworthy, modern. Lean financial-professional with warmth. The palette skews cool/blue but is rescued from corporate sterility by **Twill Brown** — a warm, paper-like neutral that humanizes everything it touches.

**Six values** (use these as content scaffolding when writing copy):

| Value | One-liner |
|---|---|
| Attain Integrity | Pursue success the right way; highest standards. |
| Attain Agility | Embrace change as opportunity; flexibility, vision, purpose. |
| Attain Trust | Build lasting relationships through honesty and respect. |
| Attain Excellence | Urgency, passion, discipline; entrepreneurial spirit. |
| Attain Accountability | Keep our word; show up for each other. |
| Attain Humility | Lead by listening, learning, lifting others up. |

### 1.2 Signature visual motif

The brand's distinguishing geometry is the **diagonal wedge composition**: large Venice Blue wedge rising from the bottom-right, smaller Curious Blue wedge from the bottom-left, with a Twill Brown sliver bridging them. The logo crystal repeats the same idea vertically — overlapping triangular facets in Venice, Curious, Matisse, and Twill Brown.

**Implication for digital UI:** lean into angled hero sections, diagonal section breaks, and triangular accent shapes. Avoid pure flat rectangles for primary brand surfaces — they read off-brand.

---

## 2. Color System

### 2.1 Primary palette (brand colors)

| Token | Name | HEX | RGB | Pantone | Role |
|---|---|---|---|---|---|
| `--color-venice-blue` | Venice Blue | `#094682` | 9,70,130 | 301 C | **Primary brand.** Headings, primary buttons, logo wordmark, navigation. |
| `--color-curious-blue` | Curious Blue | `#1D96D3` | 29,150,211 | 801 C | Accent / link / focus. Subheadings, highlights, hover states. |
| `--color-kashmir-blue` | Kashmir Blue | `#51779D` | 81,119,157 | 646 C | Muted brand. Secondary text, dividers, table headers. |
| `--color-matisse` | Matisse | `#197C98` | 25,124,152 | 314 C | Teal-leaning blue. Secondary CTAs, charts, info states. |
| `--color-twill-brown` | Twill Brown | `#DFD3B8` | 223,211,184 | 7500 C | **Warm neutral.** Backgrounds, callouts, "humanizing" surfaces. |

### 2.2 Secondary palette (extended chart & status colors)

Organized in three tonal rows. Use the **mid row** for primary data viz, the **light row** for backgrounds/badges, the **dark row** for emphasis or dark-mode surfaces.

| Hue | Light | Mid | Dark |
|---|---|---|---|
| Red | `#F37376` | `#ED1C24` | `#9F1D20` |
| Orange | `#F9A246` | `#F37221` | `#F26322` |
| Yellow | `#F9F07A` | `#F4E25B` | `#F7CD0F` |
| Green | `#68B756` | `#0C6B4D` | `#073736` |
| Blue (alt) | `#C9E7F4` | `#2675BC` | `#1D3E50` |
| Tan | `#EBE5DA` | `#B49C79` | `#5B5730` |
| Gray | `#E9EBEE` | `#AEB8C7` | `#36404F` |

### 2.3 Semantic tokens (light theme)

Always reference semantic tokens in product code, not raw palette tokens. This is what lets dark mode and rebrands work without rewriting every component.

```css
:root {
  /* Surfaces */
  --bg-canvas:       #FFFFFF;
  --bg-subtle:       #F7F8FA;          /* near-white, gray-50 */
  --bg-muted:        #E9EBEE;          /* secondary gray light */
  --bg-warm:         #EBE5DA;          /* twill brown light */
  --bg-inverse:      #094682;          /* venice blue */

  /* Text */
  --text-primary:    #094682;          /* venice blue — headings */
  --text-body:       #1D3E50;          /* dark blue — body */
  --text-muted:      #51779D;          /* kashmir blue — secondary */
  --text-on-dark:    #FFFFFF;
  --text-on-warm:    #094682;

  /* Borders */
  --border-default:  #AEB8C7;
  --border-strong:   #51779D;
  --border-focus:    #1D96D3;

  /* Brand */
  --brand-primary:   #094682;          /* venice blue */
  --brand-accent:    #1D96D3;          /* curious blue */
  --brand-warm:      #DFD3B8;          /* twill brown */
  --brand-deep:      #197C98;          /* matisse */

  /* Status (semantic, NOT raw palette) */
  --status-success-bg:  #E8F3E5;
  --status-success-fg:  #0C6B4D;
  --status-warning-bg:  #FDF1D9;
  --status-warning-fg:  #B07A00;
  --status-danger-bg:   #FCE4E5;
  --status-danger-fg:   #9F1D20;
  --status-info-bg:     #C9E7F4;
  --status-info-fg:     #094682;

  /* Interactive */
  --action-primary-bg:        #094682;
  --action-primary-bg-hover:  #0B5AA8;
  --action-primary-fg:        #FFFFFF;
  --action-accent-bg:         #1D96D3;
  --action-accent-bg-hover:   #1680B8;
}
```

### 2.4 Dark mode (derived)

The brand guidelines are light-first. This dark palette is **derived** to maintain brand feel — Venice Blue stays, but is paired with a deeper navy canvas drawn from the secondary palette (`#1D3E50`, `#36404F`). Twill Brown remains the warm accent; it pops beautifully against dark navy.

```css
[data-theme="dark"] {
  --bg-canvas:       #0F2236;          /* deeper than venice blue */
  --bg-subtle:       #1D3E50;          /* secondary dark blue */
  --bg-muted:        #36404F;          /* secondary dark gray */
  --bg-warm:         #2A2620;          /* twill brown, deepened */
  --bg-inverse:      #FFFFFF;

  --text-primary:    #FFFFFF;
  --text-body:       #E9EBEE;
  --text-muted:      #AEB8C7;
  --text-on-dark:    #FFFFFF;
  --text-on-warm:    #DFD3B8;

  --border-default:  #36404F;
  --border-strong:   #51779D;
  --border-focus:    #1D96D3;

  --brand-primary:   #1D96D3;          /* shift to curious blue — better contrast */
  --brand-accent:    #DFD3B8;          /* twill brown becomes the pop */
  --brand-warm:      #DFD3B8;
  --brand-deep:      #197C98;

  --action-primary-bg:        #1D96D3;
  --action-primary-bg-hover:  #51B5E8;
  --action-primary-fg:        #0F2236;
  --action-accent-bg:         #DFD3B8;
  --action-accent-bg-hover:   #EFE5C8;
}
```

> Venice Blue `#094682` on dark navy `#0F2236` fails WCAG AA — that's why dark mode promotes Curious Blue to the primary action role. Always verify contrast on real backgrounds before shipping.

### 2.5 Color usage rules

- **60 / 30 / 10:** ~60% neutral (white/gray/twill), ~30% Venice Blue family, ~10% Curious Blue + Twill Brown for accent.
- **Never** put Curious Blue text on white smaller than 18pt — fails AA. Use Venice Blue for body and reserve Curious Blue for headings ≥24pt, links, and large UI elements.
- **Twill Brown** is a background/accent only. Don't set body text in Twill Brown.
- **Status colors** are semantic — don't repurpose `status-danger` for decorative red.
- Chart palettes should use **primary blues first**, then move into the secondary palette only when you need more series. See §6.

---

## 3. Typography

### 3.1 Font stack

| Tier | Font | Use | Fallback |
|---|---|---|---|
| **Primary** | ITC Avant Garde Gothic Pro | Headings, brand surfaces, marketing | Century Gothic, "Avenir Next", system-ui |
| **Document** | Century Gothic | Default in the PowerPoint/Word theme (already auto-loaded by `.thmx`) | "Avant Garde", system-ui |
| **UI / body** | Inter (web) | Long-form reading, dashboards, tables, forms | system-ui, -apple-system, "Segoe UI" |
| **Mono** | JetBrains Mono | Code, IDs, monetary fixed-width data | ui-monospace, Menlo, Consolas |

```css
:root {
  --font-display: "ITC Avant Garde Gothic Pro", "Century Gothic", "Avenir Next", system-ui, sans-serif;
  --font-body:    "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, Menlo, Consolas, monospace;
}
```

> **Why two fonts on web:** ITC Avant Garde Gothic Pro is geometric and beautiful at display sizes but tiring for body text in dashboards. Inter at 14–16px is more legible for dense product UI. The brand uses Avant Garde for the wordmark and section heads; Inter handles everything else. This matches how the PowerPoint template uses Century Gothic for body — same instinct, web-appropriate execution.

### 3.2 Weights

ITC Avant Garde Gothic Pro: **Book** (400), **Medium** (500), **Bold** (700).
Inter: **400**, **500**, **600**, **700**.

Don't use weights outside this set. No black, no thin/light — they break the brand feel.

### 3.3 Type scale (web)

Modular scale, ratio 1.25 (major third), base 16px.

| Token | Size | Line height | Weight | Font | Use |
|---|---|---|---|---|---|
| `text-display` | 56px / 3.5rem | 1.05 | 700 | display | Hero headlines |
| `text-h1` | 40px / 2.5rem | 1.1 | 700 | display | Page titles |
| `text-h2` | 32px / 2rem | 1.15 | 500 | display | Section heads |
| `text-h3` | 24px / 1.5rem | 1.2 | 500 | display | Subsections |
| `text-h4` | 20px / 1.25rem | 1.3 | 500 | display | Card titles |
| `text-lead` | 18px / 1.125rem | 1.5 | 400 | body | Intro paragraphs |
| `text-body` | 16px / 1rem | 1.55 | 400 | body | Default |
| `text-sm` | 14px / 0.875rem | 1.5 | 400 | body | Secondary, meta |
| `text-xs` | 12px / 0.75rem | 1.4 | 500 | body | Labels, badges |
| `text-mono` | 14px | 1.5 | 400 | mono | Code, IDs |

### 3.4 Type rules

- **Headings:** Venice Blue (`--text-primary`) by default. Curious Blue for subheads/eyebrows under H1s — matches PPT template pattern.
- **Letter-spacing:** display font is geometric; +0.5–1% tracking on uppercase. Never on lowercase.
- **Don't use all-caps below 14px** — geometric sans-serifs get illegible.
- **Numbers in tables:** use `font-variant-numeric: tabular-nums` so columns align.

---

## 4. Logo

### 4.1 Variants

| Variant | When to use |
|---|---|
| Primary (vertical: crystal + wordmark stacked) | Default. Marketing hero, deck covers, business cards. |
| Secondary (horizontal: crystal + wordmark side-by-side) | App headers, narrow surfaces, footers. |
| 1-color greyscale | When 4-color printing isn't available. |
| 1-color black | Monochrome contexts, faxes, legal docs. |
| 1-color white | On Venice Blue or photographic dark backgrounds. |
| Crystal mark only | App icons, favicons, watermark on slides (bottom-right). |

### 4.2 Clear space

Minimum clear space around the logo = the width of the wordmark's "A". Don't violate this with adjacent text, edges, or other logos.

### 4.3 Don'ts

- Don't recolor the crystal facets. The four-color crystal (Venice / Curious / Matisse / Twill) is fixed.
- Don't stretch, rotate, or skew.
- Don't place full-color logo on busy photography — use the white 1-color variant.
- Don't reconstruct the wordmark from system fonts. Use the SVG.
- Minimum size: **120px wide** for the horizontal lockup; **80px wide** for the vertical lockup. Below that, use the crystal mark alone.

---

## 5. Layout & Spacing

### 5.1 Spacing scale

4px base unit. Linear at small sizes, geometric at large.

| Token | Value | Pixels |
|---|---|---|
| `space-0` | 0 | 0 |
| `space-1` | 0.25rem | 4 |
| `space-2` | 0.5rem | 8 |
| `space-3` | 0.75rem | 12 |
| `space-4` | 1rem | 16 |
| `space-5` | 1.5rem | 24 |
| `space-6` | 2rem | 32 |
| `space-7` | 3rem | 48 |
| `space-8` | 4rem | 64 |
| `space-9` | 6rem | 96 |
| `space-10` | 8rem | 128 |

### 5.2 Radii

The brand geometry is angular (wedges, crystal facets), so **keep radii subtle**. Avoid soft, rounded "friendly" UI — it fights the wordmark.

| Token | Value | Use |
|---|---|---|
| `radius-none` | 0 | Wedge sections, brand shapes |
| `radius-sm` | 2px | Inputs, badges |
| `radius-md` | 4px | Buttons, cards |
| `radius-lg` | 8px | Modals, large cards |
| `radius-pill` | 9999px | Status pills only |

### 5.3 Elevation

Restrained shadows. Financial brands lose trust with neumorphic puffiness.

```css
--shadow-sm: 0 1px 2px rgba(9, 70, 130, 0.06);
--shadow-md: 0 4px 8px rgba(9, 70, 130, 0.08), 0 1px 2px rgba(9, 70, 130, 0.04);
--shadow-lg: 0 12px 24px rgba(9, 70, 130, 0.10), 0 4px 8px rgba(9, 70, 130, 0.06);
--shadow-focus: 0 0 0 3px rgba(29, 150, 211, 0.35);  /* curious blue glow */
```

Shadow tint uses Venice Blue with low alpha — feels more on-brand than neutral gray shadow.

### 5.4 Grid

- Marketing: 12-column, 1280px max content width, 24px gutter, 64–96px section padding.
- App: 12-column, fluid up to 1440px, 16px gutter, 24–32px section padding.
- Mobile: 4-column, 16px gutter, 16px page padding.

### 5.5 The brand wedge

The diagonal Venice / Curious / Twill wedge composition is the signature layout flourish. Use it sparingly and only on **brand surfaces**: landing page hero, section dividers, deck title pages, cover slides. Don't litter it across product UI.

**Web implementation:**

```css
.brand-wedge {
  position: absolute;
  inset-block-end: 0;
  inset-inline: 0;
  height: 240px;
  background:
    linear-gradient(115deg, transparent 60%, var(--color-venice-blue) 60%),
    linear-gradient(70deg, var(--color-curious-blue) 30%, transparent 30%),
    linear-gradient(95deg, transparent 28%, var(--color-twill-brown) 28%, var(--color-twill-brown) 32%, transparent 32%);
  background-size: 100% 100%, 100% 60%, 100% 40%;
  background-position: bottom right, bottom left, bottom center;
  background-repeat: no-repeat;
}
```

Or rebuild as SVG for crisp scaling — preferred.

---

## 6. Data Visualization

The PPT template establishes a clear chart palette pattern. Match it on web.

### 6.1 Sequential / single-series

Use the primary blue ramp: `#094682` → `#197C98` → `#1D96D3` → `#51779D` → `#C9E7F4`.

### 6.2 Categorical (up to 8 series)

In order — don't skip around:

1. Venice Blue `#094682`
2. Curious Blue `#1D96D3`
3. Twill Brown `#DFD3B8`
4. Matisse `#197C98`
5. Kashmir Blue `#51779D`
6. Mid Green `#0C6B4D`
7. Mid Orange `#F37221`
8. Mid Red `#ED1C24`

### 6.3 Diverging (e.g., performance variance)

Red mid (`#ED1C24`) ← Tan (`#EBE5DA`) → Green mid (`#0C6B4D`).

### 6.4 Chart rules

- Gridlines: `--border-default` at 50% opacity.
- Axes: `--text-muted`.
- Labels: 12px, `--text-body`.
- Tooltips: `--bg-canvas` background, `--shadow-md`, `--border-default` border.
- Currency: always `tabular-nums`, trailing 2 decimals for under $1M, no decimals above.

---

## 7. Iconography

The PPT icon set is **flat, 2-tone, filled silhouettes** — Venice Blue + Curious Blue. Themes are heavily financial: money, security, communication, charts.

**For web/app icons:**

- Prefer **outlined icons at 1.5px stroke** (Lucide / Heroicons outline) for product UI density.
- Use the brand 2-tone filled style for marketing illustrations and dashboard category icons.
- Sizes: 16, 20, 24, 32, 48, 64px.
- Color: inherit `currentColor` for outlined icons; use Venice + Curious for 2-tone.

Don't mix outlined and filled in the same row.

---

## 8. Components (web)

Conventions for the most common product patterns. Build these once, reuse everywhere.

### 8.1 Buttons

| Variant | Background | Text | Border | Hover |
|---|---|---|---|---|
| Primary | `--action-primary-bg` (Venice) | white | none | bg → `--action-primary-bg-hover` |
| Accent | `--action-accent-bg` (Curious) | white | none | bg → `--action-accent-bg-hover` |
| Secondary | transparent | Venice Blue | 1px Venice Blue | bg → `rgba(9,70,130,0.06)` |
| Ghost | transparent | Venice Blue | none | bg → `rgba(9,70,130,0.06)` |
| Danger | `--status-danger-fg` | white | none | darken 8% |

All buttons: `radius-md` (4px), `padding: 10px 20px`, `font-weight: 500`, `font-family: --font-body`.
Focus ring: `--shadow-focus` (Curious Blue glow).

### 8.2 Forms

- Inputs: `radius-sm` (2px), 1px `--border-default`, 40px height, 12px horizontal padding.
- Focus: border → `--border-focus`, plus `--shadow-focus`.
- Error: border → `--status-danger-fg`, help text in `--status-danger-fg`.
- Labels: `text-sm`, weight 500, `--text-body`. Always above the input, never floating.

### 8.3 Cards

- Background `--bg-canvas`, border 1px `--border-default`, `radius-lg`, `--shadow-sm`.
- Hover (interactive cards): `--shadow-md`, border → `--border-strong`.
- Padding: 24px (`space-5`).

### 8.4 Tables

- Header row: `--bg-subtle` background, `text-xs` uppercase, `--text-muted`.
- Row dividers: 1px `--border-default`.
- Hover row: `--bg-subtle`.
- Numeric cells: right-aligned, `tabular-nums`.

### 8.5 Status pills

`radius-pill`, padding `2px 10px`, `text-xs` weight 500. Use status semantic tokens (§2.3).

### 8.6 Navigation (app shell)

- Top bar: Venice Blue background, white text, 56px tall. Logo crystal at left (28px), nav links 14px medium.
- Side nav (alt): white background, Venice Blue active state, Twill Brown subtle hover (`rgba(223,211,184,0.4)`).

---

## 9. Documents & Decks

### 9.1 PowerPoint / Word / Excel

**Two slide masters:**

- **Standard** — internal decks and external decks containing only publicly released information.
- **Confidential & Proprietary** — external decks with non-public information. Every slide carries the "Confidential & Proprietary" mark. To convert an existing slide, re-apply the same layout from the C&P master.

**Slide size:** 13.33" × 7.5" (widescreen 16:9).

**Available layouts** (both masters): Cover 1 / Cover 2, Section Header 1 / 2, White Content, Blue Content, Tan Content, White/Blue/Tan Two-Content, Color Block + Chart, Content/Photo, Title Only, Blank with Logo, Blank.

### 9.2 Authoring rules

- **Type directly into the placeholders** — copy/paste from external sources strips the theme's default font/size/color.
- Body type: Century Gothic (loaded by the theme). Headings: Avant Garde where available.
- The page number + crystal mark sits bottom-right on every content slide. Don't remove it.
- Cover slides use the brand wedge composition — don't replace with photography unless using the Photo Page layout.

### 9.3 PDF exports

Embed fonts on export. Avant Garde Gothic Pro is licensed — confirm the export device has it or it will substitute and break the brand.

---

## 10. Accessibility

Non-negotiable, especially for a financial product.

- **Contrast:** WCAG AA minimum (4.5:1 body, 3:1 large). Verify on every brand color combination — Curious Blue on white is borderline at body sizes.
- **Focus:** every interactive element must have a visible focus indicator (`--shadow-focus`).
- **Color is never the only signal.** Status uses color + icon + text label.
- **Motion:** respect `prefers-reduced-motion`. No essential information conveyed by animation alone.
- **Forms:** label every input. Error messages must be programmatically associated (`aria-describedby`).
- **Touch targets:** 44×44px minimum on mobile.

---

## 11. Tailwind config snippet

Drop-in starter (`tailwind.config.js`) that maps the design tokens:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        venice:   { DEFAULT: "#094682", 600: "#0B5AA8" },
        curious:  { DEFAULT: "#1D96D3", 600: "#1680B8" },
        kashmir:  "#51779D",
        matisse:  "#197C98",
        twill:    { DEFAULT: "#DFD3B8", light: "#EBE5DA", dark: "#B49C79" },
        ink:      { DEFAULT: "#1D3E50", muted: "#51779D" },
        surface:  { DEFAULT: "#FFFFFF", subtle: "#F7F8FA", muted: "#E9EBEE" },
      },
      fontFamily: {
        display: ['"ITC Avant Garde Gothic Pro"', '"Century Gothic"', '"Avenir Next"', "system-ui", "sans-serif"],
        body:    ["Inter", "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        mono:    ['"JetBrains Mono"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: { none: "0", sm: "2px", md: "4px", lg: "8px", pill: "9999px" },
      boxShadow: {
        sm: "0 1px 2px rgba(9, 70, 130, 0.06)",
        md: "0 4px 8px rgba(9, 70, 130, 0.08), 0 1px 2px rgba(9, 70, 130, 0.04)",
        lg: "0 12px 24px rgba(9, 70, 130, 0.10), 0 4px 8px rgba(9, 70, 130, 0.06)",
        focus: "0 0 0 3px rgba(29, 150, 211, 0.35)",
      },
    },
  },
};
```

---

## 12. Quick reference card

| Need | Use |
|---|---|
| Primary action | Venice Blue button |
| Link / highlight | Curious Blue |
| Warm background | Twill Brown light (`#EBE5DA`) |
| Body text | `--text-body` (`#1D3E50`) |
| Heading | Avant Garde, Venice Blue |
| Body font (web) | Inter |
| Body font (Office) | Century Gothic |
| Chart series 1 / 2 / 3 | Venice / Curious / Twill |
| Status: success | `#0C6B4D` |
| Status: danger | `#9F1D20` |
| Card radius | 8px |
| Section padding | 64–96px |
| Brand wedge | Cover slides + landing hero only |

---

*Version 1.0 — derived from Attain Finance 2025 PowerPoint Overview and brand guidelines. Update this file when the brand guidelines revise.*

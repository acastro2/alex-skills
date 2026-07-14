# Brand binary assets (drop-in)

These are **not** committed because the source files weren't available when the plugin was built. Drop them here and the `attain-design-system` skill will use them automatically for deck production:

- `attain-theme.thmx` — the Attain Finance PowerPoint/Office theme (the master layouts, theme fonts, and palette described in DESIGN.md §9). Export it from the official Attain `.pptx` template via PowerPoint → Design → Themes → Save Current Theme.
- `attain-crystal.svg` (and/or `.png`) — the logo crystal / brand mark that sits bottom-right on content slides.
- Optionally `avant-garde/` and `century-gothic/` font files if you want to embed the licensed faces for PDF export.

Until these exist, the skill reproduces the deck master in-script from the documented specs and substitutes a Venice-Blue wedge for the crystal mark. That's on-brand in geometry and color but not pixel-identical to the official template.

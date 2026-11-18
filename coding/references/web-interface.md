# Web interfaces

Read this reference when writing, changing, or reviewing web UI code: HTML, CSS, JSX or TSX components, pages, and forms. The general standards remain in [Coding](../SKILL.md).

## Apply the Web Interface Guidelines

- **Fetch the rules fresh on each task.** Get them with `webfetch` from `https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`. Do not apply them from memory. They cover accessibility, focus states, forms, animation, typography, content, images, performance, navigation, touch, dark mode, locale, and hydration.
- **When writing UI, follow the rules as you build.** Do not wait for a review to fix what the rules already say.
- **When reviewing UI, check the named files against every rule.** Report findings in the output format the fetched file defines: grouped by file, one `file:line` finding per line. If no files are named, ask which files to review.
- **If the fetch fails, say so.** Do not guess the rules. Stop and report the error.

**Why:** the rules change upstream, so a copy here goes stale. The fetched file is the source of truth, and it carries its own output format.

Source: [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) `web-design-guidelines` (MIT, `1a2c79d`), folded into this reference on 2026-11-18.

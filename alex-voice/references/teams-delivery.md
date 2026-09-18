# Teams delivery (the HTML fragment paste)

Teams renders a message from the **HTML clipboard flavor**. It ignores pasted markdown. So a Teams draft has to exist as HTML, and it has to reach the clipboard as HTML. Getting that wrong is what produces a wall of plain text instead of headings and bullets.

## Write it as an HTML fragment

Use real block tags. Without them the browser and Teams collapse every paragraph into one wall.

- Paragraphs: `<p>...</p>`
- Headings: `<h3>...</h3>` (bold, the size Teams uses for a bold line)
- Bullets: `<ul><li>...</li></ul>`
- Inline code: `<code>...</code>`
- Code block: `<pre>...</pre>`

Keep it a fragment. No `<!DOCTYPE>`, no `<head>`, no `<style>`. Styling in the fragment fights Teams' own formatting. A markdown draft is fine to author, but convert it to this fragment before the clipboard step.

## Put it on the clipboard as HTML

Selecting text in a browser and copying is not reliable here. Set the HTML flavor directly:

```bash
osascript -e "set the clipboard to (read (POSIX file \"/abs/path/fragment.html\") as «class HTML»)"
```

Check it landed before pasting:

```bash
osascript -e 'clipboard info'   # must show «class HTML»
```

Then paste into the compose box with `Cmd+V`. Bold headings, bullets, inline code and code blocks survive.

## Eyeball it first

Open a rendered preview before pasting, so a missing block tag is visible:

```bash
open -a "Microsoft Edge" /abs/path/preview.html
```

The preview file is the fragment wrapped in a minimal `<style>` shell. The clipboard gets the bare fragment, never the wrapper.

## When it still mangles

Paste as plain text and format with Teams' own toolbar. Do not spend more rounds on the clipboard.

## Untested

Tables and mermaid are not verified through the paste. Send those as a link or a file.

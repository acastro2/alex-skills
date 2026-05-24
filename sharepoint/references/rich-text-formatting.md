# SharePoint Rich Text Formatting Reference

## innerHTML — Supported HTML in Text Controls (controlType: 4)

### Headings
```html
<h2>Section Heading</h2>
<h3>Subsection Heading</h3>
<h4>Minor Heading</h4>
```

### Text Formatting
```html
<strong>Bold text</strong>
<em>Italic text</em>
<u>Underlined text</u>
<s>Strikethrough text</s>
<sup>Superscript</sup>
<sub>Subscript</sub>
```

### Links
```html
<a href="https://example.com">Regular link</a>
<a href="https://example.com" target="_blank">Opens in new tab</a>
```

### Button-Style Links
```html
<a class="ms-rteElement-ButtonLink" href="https://example.com">Button Link</a>
```

### Lists
```html
<!-- Unordered -->
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
  <li>Nested:
    <ul>
      <li>Sub-item</li>
    </ul>
  </li>
</ul>

<!-- Ordered -->
<ol>
  <li>First</li>
  <li>Second</li>
</ol>
```

### Tables
```html
<table>
  <tbody>
    <tr>
      <th>Header 1</th>
      <th>Header 2</th>
      <th>Header 3</th>
    </tr>
    <tr>
      <td>Cell 1</td>
      <td>Cell 2</td>
      <td>Cell 3</td>
    </tr>
  </tbody>
</table>
```

### Blockquotes
```html
<blockquote>
  <p>This renders as a pull quote with a left border accent.</p>
</blockquote>
```

### Code
```html
<code>inline code</code>
<pre><code>block of code</code></pre>
```

### Horizontal Rule
```html
<hr />
```

### Font Sizes (via SharePoint classes)
```html
<span class="ms-rteFontSize-1">Extra small (8pt)</span>
<span class="ms-rteFontSize-2">Small (10pt)</span>
<span class="ms-rteFontSize-3">Medium (12pt)</span>
<span class="ms-rteFontSize-4">Large (14pt)</span>
<span class="ms-rteFontSize-5">Extra large (18pt)</span>
<span class="ms-rteFontSize-6">Huge (24pt)</span>
<span class="ms-rteFontSize-7">Giant (36pt)</span>
```

### Text Colors
```html
<span style="color: rgb(255, 0, 0);">Red text</span>
<span style="color: rgb(0, 120, 212);">Theme blue</span>
<span style="background-color: rgb(255, 255, 0);">Yellow highlight</span>
```

### Inline Styles That Survive Sanitization
- `color`
- `background-color`
- `font-size`
- `text-align`
- `font-weight`
- `font-style`
- `text-decoration`

### Tags That Are STRIPPED
- `<script>` — always removed
- `<iframe>` — use Embed web part instead
- `<style>` — removed
- `<form>`, `<input>` — removed
- `<img>` with external src — use Image web part instead
- `<img>` with data: URIs — stripped

### Best Practices
1. Use `<h2>` for main sections, `<h3>` for subsections — `<h1>` is reserved for page title
2. Use `<blockquote>` for callouts and emphasis — renders with a theme-colored left border
3. Use `<table>` for structured data comparisons
4. Use button-style links (`ms-rteElement-ButtonLink`) for CTAs within text sections
5. Avoid deep nesting — keep HTML flat and readable
6. Use `<hr>` sparingly — prefer the Divider web part for visual breaks between sections

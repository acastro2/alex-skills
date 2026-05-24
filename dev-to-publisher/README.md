# Dev.to Publisher MCP Server

Automatically publish Astro blog posts to dev.to with canonical URLs and proper metadata.

## Features

- **Parse MDX files**: Extract frontmatter (title, description, tags, series, heroImage) from your Astro blog posts
- **Convert MDX to Markdown**: Strip Astro-specific components and imports for dev.to compatibility
- **Set Canonical URLs**: Point back to your original blog for SEO benefits
- **Handle Series**: Preserve multi-part post series on dev.to
- **Image Support**: Configure hero images using publicly accessible URLs
- **Duplicate Detection**: Check if a post already exists before publishing
- **Draft Protection**: Won't publish posts marked as drafts in frontmatter

## Prerequisites

1. **Node.js 18+** installed
2. **dev.to API Key**: Get yours at https://dev.to/settings/account
3. **Astro Blog**: Your blog posts should be in MDX format with frontmatter

## Installation

```bash
# Clone or copy this skill to your opencode skills directory
cd /Users/acastro/.config/opencode/skills/dev-to-publisher

# Install dependencies
npm install

# Build the TypeScript
npm run build
```

## Configuration

### Environment Variables

```bash
export DEVTO_API_KEY="your-dev-to-api-key-here"
```

### MCP Configuration

Add to your OpenCode MCP configuration:

```json
{
  "mcpServers": {
    "dev-to-publisher": {
      "command": "node",
      "args": ["/Users/acastro/.config/opencode/skills/dev-to-publisher/dist/index.js"],
      "env": {
        "DEVTO_API_KEY": "your-dev-to-api-key-here"
      }
    }
  }
}
```

## Usage

### 1. List Recent Blog Posts

See which posts are available for publishing:

```json
{
  "tool": "list_recent_posts",
  "arguments": {
    "blog_content_path": "/Users/acastro/Developer/blog-platform-toolsmith/src/content/blog",
    "limit": 10
  }
}
```

**Returns:**
- Post slug, title, date, description
- Tags and series information
- Draft status
- Hero image presence

### 2. Publish a Post

Publish a single blog post to dev.to:

```json
{
  "tool": "publish_post",
  "arguments": {
    "blog_post_path": "/Users/acastro/Developer/blog-platform-toolsmith/src/content/blog/my-awesome-post.mdx",
    "canonical_url": "https://toolsmithplatform.com/blog/my-awesome-post",
    "publish_immediately": true,
    "main_image_url": "https://toolsmithplatform.com/assets/blog/hero-image.jpg"
  }
}
```

**Parameters:**
- `blog_post_path`: Full path to your MDX file
- `canonical_url`: The production URL of your blog post (required for SEO)
- `publish_immediately`: Set to `false` to save as draft (default: `true`)
- `main_image_url`: Optional override for hero image (see Image Handling below)

**Returns:**
- `success`: Boolean indicating if publication succeeded
- `url`: The dev.to post URL on success
- `error`: Error message if publication failed

### 3. Check if Post Already Exists

Before publishing, verify a post hasn't been published already:

```json
{
  "tool": "check_post_exists",
  "arguments": {
    "canonical_url": "https://toolsmithplatform.com/blog/my-awesome-post"
  }
}
```

## Image Handling

**IMPORTANT**: The dev.to API requires publicly accessible image URLs. Your Astro blog stores images locally in `src/assets/blog/`, which aren't accessible to dev.to.

### Recommended Workflow:

1. **Deploy your blog first** to Netlify (or your hosting provider)
2. **Use production URLs** for images:
   ```json
   {
     "main_image_url": "https://toolsmithplatform.com/assets/blog/hero-image.jpg"
   }
   ```

3. **The skill will auto-construct URLs** from your `heroImage` frontmatter:
   ```yaml
   # Your MDX frontmatter
   heroImage:
     src: "/assets/blog/hero-image.jpg"
     alt: "Description"
   ```
   
   The skill combines this with your canonical URL domain to create:
   `https://toolsmithplatform.com/assets/blog/hero-image.jpg`

### Alternative: Manual Image URL

You can manually provide a fully-qualified URL:

```json
{
  "tool": "publish_post",
  "arguments": {
    "blog_post_path": "/path/to/post.mdx",
    "canonical_url": "https://yourblog.com/blog/post",
    "main_image_url": "https://cdn.example.com/images/hero.jpg"
  }
}
```

### Inline Images in Content

For images within your markdown content, ensure they use publicly accessible URLs:

```markdown
<!-- Good - public URL -->
![Diagram](https://yourblog.com/assets/blog/diagram.png)

<!-- Bad - local path won't work -->
![Diagram](../../assets/blog/diagram.png)
```

## Frontmatter Mapping

| Astro Frontmatter | dev.to Field | Notes |
|------------------|--------------|-------|
| `title` | `title` | Required |
| `description` | `description` | Optional |
| `tags` | `tags` | Max 4 tags, comma-separated |
| `series` | `series` | Must match existing dev.to series |
| `heroImage.src` | `main_image` | Auto-converted to full URL |
| `date` | - | Used for sorting |
| `draft` | - | Blocks publishing if `true` |

## Workflow Examples

### Complete Publishing Workflow:

1. **Write and commit your post** in your Astro blog
2. **Deploy your blog** (Netlify will auto-deploy on push)
3. **Use the skill** to publish:
   ```
   "List recent posts from /Users/acastro/Developer/blog-platform-toolsmith/src/content/blog"
   
   "Publish my-post.mdx to dev.to with canonical URL https://toolsmithplatform.com/blog/my-post"
   ```

### Publishing a Series:

For multi-part posts, ensure the `series` field matches across all parts:

```yaml
# Part 1
series: "senior-engineer-journey"

# Part 2
series: "senior-engineer-journey"
```

Dev.to will automatically group these posts together.

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Invalid API key | Verify `DEVTO_API_KEY` environment variable |
| `422 Unprocessable Entity` | Invalid data | Check tags format (comma-separated), URL format |
| `Post already exists on dev.to` | Duplicate canonical URL | Use `check_post_exists` first or update existing post |
| `Post is marked as draft` | `draft: true` in frontmatter | Change to `draft: false` or remove the field |
| Images not showing | Local file paths | Use public URLs or deploy blog first |

## Development

```bash
# Build the TypeScript
npm run build

# Watch mode for development
npm run dev

# Test manually
npm start
```

## Limitations

1. **No Image Upload API**: dev.to doesn't expose an image upload endpoint via API. You must use publicly accessible image URLs.
2. **No Update Function**: Currently only creates new posts. To update, use dev.to's web interface or implement the `PUT /articles/{id}` endpoint.
3. **Tag Limit**: Maximum 4 tags on dev.to (extra tags are truncated).
4. **Series Creation**: Series must be created on dev.to web interface first; API can only assign to existing series.

## Future Enhancements

- [ ] Update existing posts via API
- [ ] Bulk publish multiple posts
- [ ] Automatic image upload to CDN
- [ ] Post scheduling
- [ ] Draft preview before publishing

## License

ISC

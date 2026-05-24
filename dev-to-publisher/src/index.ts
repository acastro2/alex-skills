#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import matter from "gray-matter";
import { readFileSync, existsSync, writeFileSync, mkdtempSync, rmSync } from "fs";
import { join, basename, dirname } from "path";
import { tmpdir } from "os";
import { z } from "zod";
import { chromium } from "playwright";

const DEVTO_API_BASE = "https://dev.to/api";
const API_KEY = process.env.DEVTO_API_KEY;

if (!API_KEY) {
  console.error("Error: DEVTO_API_KEY environment variable is required");
  process.exit(1);
}

const BlogFrontmatterSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
  date: z.union([z.date(), z.string()]),
  updatedDate: z.union([z.date(), z.string()]).optional(),
  heroImage: z.object({
    src: z.string(),
    alt: z.string(),
  }).optional(),
  tags: z.array(z.string()).default([]),
  series: z.string().optional(),
  draft: z.boolean().default(false),
});

type BlogFrontmatter = z.infer<typeof BlogFrontmatterSchema>;

interface BlogPost {
  frontmatter: BlogFrontmatter;
  content: string;
  filePath: string;
  slug: string;
}

const tools: Tool[] = [
  {
    name: "list_recent_posts",
    description: "List recent blog posts from the Astro blog that can be published to dev.to",
    inputSchema: {
      type: "object",
      properties: {
        blog_content_path: {
          type: "string",
          description: "Path to the blog content directory containing MDX files (e.g., /Users/acastro/Developer/blog-platform-toolsmith/src/content/blog)",
        },
        limit: {
          type: "number",
          description: "Maximum number of posts to return (default: 10)",
          default: 10,
        },
      },
      required: ["blog_content_path"],
    },
  },
  {
    name: "publish_post",
    description: "Publish a blog post to dev.to as a DRAFT (never directly published) with canonical URL pointing to the original blog. You'll need to manually publish from dev.to dashboard after review.",
    inputSchema: {
      type: "object",
      properties: {
        blog_post_path: {
          type: "string",
          description: "Full path to the blog post MDX file to publish",
        },
        canonical_url: {
          type: "string",
          description: "Canonical URL pointing to the original blog post (e.g., https://yourblog.com/blog/post-slug)",
        },
        main_image_url: {
          type: "string",
          description: "Optional: Publicly accessible URL for the hero/main image. If not provided, will try to construct from heroImage in frontmatter",
        },
      },
      required: ["blog_post_path", "canonical_url"],
    },
  },
  {
    name: "edit_post",
    description: "Update an existing dev.to post by its article ID. Can update content, title, tags, main_image, etc.",
    inputSchema: {
      type: "object",
      properties: {
        article_id: {
          type: "number",
          description: "The dev.to article ID to edit (from the article URL)",
        },
        blog_post_path: {
          type: "string",
          description: "Full path to the blog post MDX file to update the post with",
        },
        canonical_url: {
          type: "string",
          description: "Canonical URL pointing to the original blog post",
        },
        main_image_url: {
          type: "string",
          description: "Optional: Publicly accessible URL for the hero/main image",
        },
      },
      required: ["article_id", "blog_post_path", "canonical_url"],
    },
  },
  {
    name: "check_post_exists",
    description: "Check if a blog post has already been published to dev.to by searching for the canonical URL",
    inputSchema: {
      type: "object",
      properties: {
        canonical_url: {
          type: "string",
          description: "The canonical URL to search for on dev.to",
        },
      },
      required: ["canonical_url"],
    },
  },
];

async function parseBlogPost(filePath: string): Promise<BlogPost> {
  if (!existsSync(filePath)) {
    throw new Error(`Blog post file not found: ${filePath}`);
  }

  const fileContent = readFileSync(filePath, "utf-8");
  const parsed = matter(fileContent);

  const frontmatter = BlogFrontmatterSchema.parse(parsed.data);
  const slug = basename(filePath, ".mdx").replace(/\.md$/, "");

  return {
    frontmatter,
    content: parsed.content,
    filePath,
    slug,
  };
}

function convertMdxToMarkdown(content: string, blogDomain: string): string {
  // Remove Astro-specific imports and components
  let markdown = content;

  // Remove import statements for Astro components
  markdown = markdown.replace(/^import\s+.*?\s+from\s+['"].*?['"];?\s*$/gm, "");

  // Remove Astro component tags (keep content inside)
  markdown = markdown.replace(/<\w+[^>]*>([\s\S]*?)<\/\w+>/g, "$1");

  // Convert relative image paths to absolute URLs
  // Markdown syntax: ![alt](/assets/...) -> ![alt](https://domain/assets/...)
  markdown = markdown.replace(
    /!\[([^\]]*)\]\((\/?assets\/[^)]+)\)/g,
    (match, alt, path) => {
      const cleanPath = path.replace(/^\//, "");
      return `![${alt}](${blogDomain}/${cleanPath})`;
    }
  );

  // HTML img tags: <img src="/assets/..." /> -> <img src="https://domain/assets/..." />
  markdown = markdown.replace(
    /<img\s+[^>]*src=["'](\/?assets\/[^"']+)["'][^>]*>/gi,
    (match, path) => {
      const cleanPath = path.replace(/^\//, "");
      return match.replace(path, `${blogDomain}/${cleanPath}`);
    }
  );

  // Clean up excessive newlines
  markdown = markdown.replace(/\n{3,}/g, "\n\n");

  return markdown.trim();
}

async function renderMermaidToImage(diagramContent: string, index: number): Promise<Buffer | null> {
  const tempDir = mkdtempSync(join(tmpdir(), "mermaid-"));
  const htmlPath = join(tempDir, `diagram-${index}.html`);
  
  try {
    // Escape the diagram content for safe HTML insertion
    const escapedContent = diagramContent
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    
    // Create HTML with mermaid
    const html = `<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'default' });
  </script>
  <style>
    body { margin: 0; padding: 20px; background: white; }
    .mermaid { display: flex; justify-content: center; }
  </style>
</head>
<body>
  <div class="mermaid">
${escapedContent}
  </div>
</body>
</html>`;
    
    writeFileSync(htmlPath, html);
    
    // Launch browser and render
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto(`file://${htmlPath}`, { waitUntil: 'networkidle' });
    
    // Wait for mermaid to render with a longer timeout
    await page.waitForSelector('.mermaid svg', { timeout: 30000 });
    
    // Get the SVG element
    const svgElement = await page.locator('.mermaid svg').first();
    const box = await svgElement.boundingBox();
    
    if (!box) {
      throw new Error('Could not get bounding box for mermaid diagram');
    }
    
    // Take screenshot of the SVG
    const screenshot = await page.screenshot({
      clip: { x: box.x - 10, y: box.y - 10, width: box.width + 20, height: box.height + 20 }
    });
    
    await browser.close();
    
    return screenshot;
  } catch (error) {
    console.error(`Error rendering mermaid diagram ${index}:`, error);
    return null;
  } finally {
    // Clean up temp files
    try {
      rmSync(tempDir, { recursive: true, force: true });
    } catch (e) {
      // Ignore cleanup errors
    }
  }
}

async function uploadImageToDevTo(imageBuffer: Buffer, filename: string): Promise<string | null> {
  try {
    // Use Imgur anonymous API to upload the image
    // Note: This uses anonymous uploads which are public but don't require auth
    const base64 = imageBuffer.toString('base64');
    
    const response = await fetch('https://api.imgur.com/3/image', {
      method: 'POST',
      headers: {
        'Authorization': 'Client-ID 546c25a59c58ad7', // Public anonymous client ID
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        image: base64,
        type: 'base64',
        title: filename,
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      console.error('Imgur upload failed:', errorData);
      
      // Fallback: try with base64 data URI (some platforms support this)
      return `data:image/png;base64,${base64}`;
    }
    
    const data = await response.json();
    
    if (data.success && data.data && data.data.link) {
      console.error(`Image uploaded to Imgur: ${data.data.link}`);
      return data.data.link;
    }
    
    // Fallback if Imgur returns unexpected format
    return `data:image/png;base64,${base64}`;
  } catch (error) {
    console.error("Error uploading image to Imgur:", error);
    // Fallback to base64 data URI
    try {
      const base64 = imageBuffer.toString('base64');
      return `data:image/png;base64,${base64}`;
    } catch (e) {
      return null;
    }
  }
}

async function convertMdxToMarkdownAsync(content: string, blogDomain: string): Promise<string> {
  // First, do the basic conversions
  let markdown = convertMdxToMarkdown(content, blogDomain);
  
  // Find and render mermaid diagrams
  const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
  const matches = [...markdown.matchAll(mermaidRegex)];
  
  console.error(`Found ${matches.length} mermaid diagrams to render`);
  
  if (matches.length === 0) {
    return markdown;
  }
  
  // Render each mermaid diagram
  for (let i = matches.length - 1; i >= 0; i--) {
    const match = matches[i];
    const diagramContent = match[1];
    const fullMatch = match[0];
    
    console.error(`Rendering mermaid diagram ${i + 1}/${matches.length}...`);
    
    try {
      const imageBuffer = await renderMermaidToImage(diagramContent, i);
      
      if (imageBuffer) {
        console.error(`Diagram ${i + 1} rendered successfully (${imageBuffer.length} bytes)`);
        const imageUrl = await uploadImageToDevTo(imageBuffer, `diagram-${i}.png`);
        if (imageUrl) {
          console.error(`Diagram ${i + 1} uploaded successfully`);
          // Replace the mermaid block with an image
          markdown = markdown.replace(fullMatch, `![Mermaid diagram ${i + 1}](${imageUrl})`);
        } else {
          console.error(`Diagram ${i + 1} upload failed, keeping original with note`);
          // Keep the original but add a note
          markdown = markdown.replace(fullMatch, `${fullMatch}\n\n*[Mermaid diagram above - upload failed]*`);
        }
      } else {
        console.error(`Diagram ${i + 1} render failed, keeping original with note`);
        // Keep the original but add a note
        markdown = markdown.replace(fullMatch, `${fullMatch}\n\n*[Mermaid diagram above - render failed]*`);
      }
    } catch (error) {
      console.error(`Error processing diagram ${i + 1}:`, error);
      // Keep the original mermaid block as fallback
      markdown = markdown.replace(fullMatch, `${fullMatch}\n\n*[Mermaid diagram above - error: ${error}]*`);
    }
  }
  
  return markdown;
}

function constructImageUrl(
  heroImage: BlogFrontmatter["heroImage"],
  blogDomain: string
): string | undefined {
  if (!heroImage) return undefined;

  // If it's already a full URL, use it
  if (heroImage.src.startsWith("http://") || heroImage.src.startsWith("https://")) {
    return heroImage.src;
  }

  // Remove leading slash if present
  const cleanPath = heroImage.src.replace(/^\//, "");
  const domain = blogDomain.replace(/\/$/, "");

  return `${domain}/${cleanPath}`;
}

async function publishToDevTo(
  post: BlogPost,
  canonicalUrl: string,
  mainImageUrl?: string
): Promise<{ success: boolean; url?: string; error?: string }> {
  try {
    // Extract domain from canonical URL for image construction
    const blogDomain = new URL(canonicalUrl).origin;
    
    const markdownContent = await convertMdxToMarkdownAsync(post.content, blogDomain);

    // Determine main image URL
    const finalMainImage = mainImageUrl || constructImageUrl(post.frontmatter.heroImage, blogDomain);

    // Format tags for dev.to (comma-separated string, max 4 tags)
    const tags = post.frontmatter.tags.slice(0, 4).join(", ");

    const articleData = {
      article: {
        title: post.frontmatter.title,
        body_markdown: markdownContent,
        published: false, // Always create as draft for manual review
        canonical_url: canonicalUrl,
        tags: tags,
        series: post.frontmatter.series || undefined,
        main_image: finalMainImage,
        description: post.frontmatter.description,
      },
    };

    const response = await fetch(`${DEVTO_API_BASE}/articles`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "api-key": API_KEY!,
      },
      body: JSON.stringify(articleData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `Dev.to API error: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`
      );
    }

    const result = await response.json();
    return {
      success: true,
      url: result.url,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

async function checkPostExists(canonicalUrl: string): Promise<{ exists: boolean; devToUrl?: string }> {
  try {
    // Search for articles with this canonical URL by checking user's articles
    // Note: dev.to doesn't have a direct search by canonical URL, so we fetch recent articles
    const response = await fetch(`${DEVTO_API_BASE}/articles/me?per_page=100`, {
      headers: {
        "api-key": API_KEY!,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch articles: ${response.status}`);
    }

    const articles = await response.json();
    const existingPost = articles.find(
      (article: any) => article.canonical_url === canonicalUrl
    );

    return {
      exists: !!existingPost,
      devToUrl: existingPost?.url,
    };
  } catch (error) {
    console.error("Error checking post existence:", error);
    return { exists: false };
  }
}

async function listRecentPosts(blogContentPath: string, limit: number = 10): Promise<BlogPost[]> {
  const { glob } = await import("glob");
  const mdxFiles = await glob("**/*.mdx", {
    cwd: blogContentPath,
    absolute: true,
  });

  const posts: BlogPost[] = [];

  for (const filePath of mdxFiles.slice(0, limit)) {
    try {
      const post = await parseBlogPost(filePath);
      posts.push(post);
    } catch (error) {
      console.error(`Error parsing ${filePath}:`, error);
    }
  }

  // Sort by date, most recent first
  posts.sort((a, b) => {
    const dateA = new Date(a.frontmatter.date);
    const dateB = new Date(b.frontmatter.date);
    return dateB.getTime() - dateA.getTime();
  });

  return posts.slice(0, limit);
}

async function editPostOnDevTo(
  articleId: number,
  post: BlogPost,
  canonicalUrl: string,
  mainImageUrl?: string
): Promise<{ success: boolean; url?: string; error?: string }> {
  try {
    // Extract domain from canonical URL for image construction
    const blogDomain = new URL(canonicalUrl).origin;
    
    const markdownContent = await convertMdxToMarkdownAsync(post.content, blogDomain);

    // Determine main image URL
    const finalMainImage = mainImageUrl || constructImageUrl(post.frontmatter.heroImage, blogDomain);

    // Format tags for dev.to (comma-separated string, max 4 tags)
    const tags = post.frontmatter.tags.slice(0, 4).join(", ");

    const articleData = {
      article: {
        title: post.frontmatter.title,
        body_markdown: markdownContent,
        published: false, // Keep as draft when editing
        canonical_url: canonicalUrl,
        tags: tags,
        series: post.frontmatter.series || undefined,
        main_image: finalMainImage,
        description: post.frontmatter.description,
      },
    };

    const response = await fetch(`${DEVTO_API_BASE}/articles/${articleId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "api-key": API_KEY!,
      },
      body: JSON.stringify(articleData),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        `Dev.to API error: ${response.status} ${response.statusText}. ${JSON.stringify(errorData)}`
      );
    }

    const result = await response.json();
    return {
      success: true,
      url: result.url,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

const server = new Server(
  {
    name: "dev-to-publisher",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "list_recent_posts": {
        const { blog_content_path, limit = 10 } = args as {
          blog_content_path: string;
          limit?: number;
        };

        const posts = await listRecentPosts(blog_content_path, limit);

        const formattedPosts = posts.map((post) => ({
          slug: post.slug,
          title: post.frontmatter.title,
          date: post.frontmatter.date,
          description: post.frontmatter.description,
          tags: post.frontmatter.tags,
          series: post.frontmatter.series,
          hasHeroImage: !!post.frontmatter.heroImage,
          filePath: post.filePath,
          draft: post.frontmatter.draft,
        }));

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(formattedPosts, null, 2),
            },
          ],
        };
      }

      case "publish_post": {
        const {
          blog_post_path,
          canonical_url,
          main_image_url,
        } = args as {
          blog_post_path: string;
          canonical_url: string;
          main_image_url?: string;
        };

        // First check if already published
        const existing = await checkPostExists(canonical_url);
        if (existing.exists) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  error: "Post already exists on dev.to",
                  existingUrl: existing.devToUrl,
                }, null, 2),
              },
            ],
          };
        }

        const post = await parseBlogPost(blog_post_path);

        if (post.frontmatter.draft) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  error: "Post is marked as draft in frontmatter",
                  suggestion: "Remove 'draft: true' from frontmatter or set to false",
                }, null, 2),
              },
            ],
          };
        }

        const result = await publishToDevTo(
          post,
          canonical_url,
          main_image_url
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "edit_post": {
        const {
          article_id,
          blog_post_path,
          canonical_url,
          main_image_url,
        } = args as {
          article_id: number;
          blog_post_path: string;
          canonical_url: string;
          main_image_url?: string;
        };

        const post = await parseBlogPost(blog_post_path);

        if (post.frontmatter.draft) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  success: false,
                  error: "Post is marked as draft in frontmatter",
                  suggestion: "Remove 'draft: true' from frontmatter or set to false",
                }, null, 2),
              },
            ],
          };
        }

        const result = await editPostOnDevTo(
          article_id,
          post,
          canonical_url,
          main_image_url
        );

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "check_post_exists": {
        const { canonical_url } = args as { canonical_url: string };
        const result = await checkPostExists(canonical_url);

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            error: error instanceof Error ? error.message : String(error),
          }, null, 2),
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Dev.to Publisher MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

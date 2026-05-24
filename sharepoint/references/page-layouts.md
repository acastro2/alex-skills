# SharePoint Page Layouts & Sections Reference

## Page Layout Types

Set via `PageLayoutType` on creation. Do NOT change after creation.

| Value | Use Case |
|-------|----------|
| `"Article"` | Standard content page with banner header. Default choice. |
| `"Home"` | Site home page. Wider canvas, different header behavior. |
| `"SingleWebPartAppPage"` | Full-page app — single web part fills entire page. |
| `"RepostPage"` | News repost / link to external content. |

## CanvasContent1 Structure

A JSON array containing:
- **Column descriptors** (`controlType: 0`) — define layout columns
- **Text blocks** (`controlType: 4`) — rich text content
- **Web parts** (`controlType: 3`) — interactive components
- **Page settings** (`controlType: 0` with `pageSettingsSlice`) — always last element

## Position Object

Every control has a position:
```json
{
  "zoneIndex": 1,       // Section number (1-based)
  "sectionIndex": 1,    // Column within section (1-based)
  "sectionFactor": 12,  // Column width (must sum to 12)
  "controlIndex": 1,    // Control position within column (1-based)
  "layoutIndex": 1      // 1 = normal, 2 = vertical section
}
```

## Section Layouts

### Full Width (1 column)
```
| sectionFactor: 12 |
```

### Two Equal Columns
```
| sectionFactor: 6 | sectionFactor: 6 |
```

### Three Equal Columns
```
| sectionFactor: 4 | sectionFactor: 4 | sectionFactor: 4 |
```

### 1/3 + 2/3
```
| sectionFactor: 4 | sectionFactor: 8 |
```

### 2/3 + 1/3
```
| sectionFactor: 8 | sectionFactor: 4 |
```

### Vertical Section (right sidebar)
Use `layoutIndex: 2` with `sectionFactor: 12`. Only one per page.

## Section Backgrounds (zoneEmphasis)

| Value | Appearance |
|-------|-----------|
| `0` or `{}` | None — white/transparent |
| `1` | Neutral — light gray |
| `2` | Soft — light theme accent |
| `3` | Strong — dark theme accent |

All controls in the same `zoneIndex` MUST share the same `zoneEmphasis`.

## Column Descriptor

Every column needs a descriptor BEFORE its controls:
```json
{
  "controlType": 0,
  "displayMode": 2,
  "emphasis": { "zoneEmphasis": 0 },
  "position": {
    "zoneIndex": 1,
    "sectionIndex": 1,
    "sectionFactor": 12,
    "layoutIndex": 1
  }
}
```

## Collapsible Sections

Add to column descriptor:
```json
{
  "controlType": 0,
  "displayMode": 2,
  "emphasis": {},
  "position": { ... },
  "collapsibleSection": {
    "isCollapsible": true,
    "isExpanded": true,
    "displayName": "Section Title",
    "showDividerLine": true
  }
}
```

## Page Header (LayoutWebpartsContent)

Controls the banner/title region. Separate from CanvasContent1.

### Header Layout Types
| Value | Description |
|-------|-------------|
| `"FullWidthImage"` | Banner image with text overlay (default) |
| `"NoImage"` | Plain colored header |
| `"ColorBlock"` | Colored block with large title |
| `"CutInShape"` | Image in irregular shape |

### Header Properties
```json
[
  {
    "dataVersion": "1.4",
    "id": "cbe7b0a9-3504-44dd-a3a3-0e5cacd07788",
    "instanceId": "cbe7b0a9-3504-44dd-a3a3-0e5cacd07788",
    "title": "Title area",
    "reservedHeight": 280,
    "properties": {
      "title": "Page Title",
      "topicHeader": "CATEGORY",
      "authorByline": ["user@tenant.com"],
      "authors": [],
      "layoutType": "FullWidthImage",
      "textAlignment": "Left",
      "showTopicHeader": true,
      "showPublishDate": true,
      "enableGradientEffect": true
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {
        "imageSource": "/sites/mysite/SiteAssets/banner.jpg"
      },
      "links": {}
    }
  }
]
```

## Page Settings Slice (always last in CanvasContent1)

```json
{
  "controlType": 0,
  "pageSettingsSlice": {
    "isDefaultDescription": true,
    "isDefaultThumbnail": true
  }
}
```

## Complete Example — Two-Column Layout

```json
[
  {
    "controlType": 0,
    "displayMode": 2,
    "emphasis": { "zoneEmphasis": 1 },
    "position": { "zoneIndex": 1, "sectionIndex": 1, "sectionFactor": 6, "layoutIndex": 1 }
  },
  {
    "controlType": 4,
    "id": "guid-1",
    "anchorComponentId": "guid-1",
    "displayMode": 2,
    "editorType": "CKEditor",
    "innerHTML": "<h2>Left Column</h2><p>Content here</p>",
    "emphasis": { "zoneEmphasis": 1 },
    "addedFromPersistedData": false,
    "position": { "zoneIndex": 1, "sectionIndex": 1, "sectionFactor": 6, "controlIndex": 1, "layoutIndex": 1 }
  },
  {
    "controlType": 0,
    "displayMode": 2,
    "emphasis": { "zoneEmphasis": 1 },
    "position": { "zoneIndex": 1, "sectionIndex": 2, "sectionFactor": 6, "layoutIndex": 1 }
  },
  {
    "controlType": 4,
    "id": "guid-2",
    "anchorComponentId": "guid-2",
    "displayMode": 2,
    "editorType": "CKEditor",
    "innerHTML": "<h2>Right Column</h2><p>Content here</p>",
    "emphasis": { "zoneEmphasis": 1 },
    "addedFromPersistedData": false,
    "position": { "zoneIndex": 1, "sectionIndex": 2, "sectionFactor": 6, "controlIndex": 1, "layoutIndex": 1 }
  },
  {
    "controlType": 0,
    "pageSettingsSlice": { "isDefaultDescription": true, "isDefaultThumbnail": true }
  }
]
```

## API Workflow

1. **Create:** `POST /_api/sitepages/pages` with `{ "PageLayoutType": "Article", "PromotedState": 0 }`
2. **Checkout:** `POST /_api/sitepages/pages({id})/checkoutpage`
3. **Save:** `POST /_api/sitepages/pages({id})/savepage` with Title, CanvasContent1, LayoutWebpartsContent
4. **Publish:** `POST /_api/sitepages/pages({id})/publish`

## Critical Rules

1. **sectionFactor** values per section MUST sum to 12
2. **zoneEmphasis** MUST be consistent across all controls in a zoneIndex
3. **Each control needs a unique id** (GUID format)
4. **id and anchorComponentId** must match for text controls
5. **id and webPartData.instanceId** must match for web parts
6. **Column descriptors** (controlType: 0) must precede their controls
7. **pageSettingsSlice** must be the last element in the array
8. **displayMode: 2** always (read mode) when saving via API

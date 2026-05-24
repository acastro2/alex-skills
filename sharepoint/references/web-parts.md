# SharePoint Web Parts — Verified GUIDs & Configuration

> GUIDs verified against `attainfinance.sharepoint.com` tenant on 2026-05-04.

## Content Web Parts

### Text (Rich Text Editor)
- **controlType:** `4` (not a standard web part)
- **No webPartId needed**
- See `rich-text-formatting.md` for innerHTML reference

### Image
- **webPartId:** `d1d91016-032f-456d-98a4-721247c305e8`
- **alias:** `ImageWebPart`

```json
{
  "controlType": 3,
  "webPartId": "d1d91016-032f-456d-98a4-721247c305e8",
  "webPartData": {
    "id": "d1d91016-032f-456d-98a4-721247c305e8",
    "instanceId": "<unique-guid>",
    "title": "Image",
    "dataVersion": "1.9",
    "properties": {
      "imageSourceType": 2,
      "altText": "Description",
      "overlayText": "",
      "isInlineImage": false,
      "imagePosition": "Center",
      "alignment": "Center",
      "fixAspectRatio": false
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {
        "imageSource": "/sites/mysite/SiteAssets/image.jpg"
      },
      "links": {}
    }
  }
}
```

### Hero
- **webPartId:** `c4bd7b2f-7b6e-4599-8485-16504575f590`
- **alias:** `HeroWebPart`
- **Layouts:** `"Tiles"`, `"Layers"`, `"VerticalLayer"`, `"SingleTile"`

```json
{
  "controlType": 3,
  "webPartId": "c4bd7b2f-7b6e-4599-8485-16504575f590",
  "webPartData": {
    "id": "c4bd7b2f-7b6e-4599-8485-16504575f590",
    "instanceId": "<guid>",
    "title": "Hero",
    "dataVersion": "1.6",
    "properties": {
      "heroLayoutThreshold": 640,
      "carouselLayoutMaxWidth": 365,
      "layoutType": "Tiles",
      "isCenteredText": false,
      "slides": [
        {
          "id": 1,
          "type": "UrlLink",
          "title": "Tile Title",
          "description": "Description text",
          "url": "https://example.com",
          "thumbnailType": 2,
          "thumbnail": {
            "imageSource": "/sites/mysite/SiteAssets/hero.jpg",
            "altText": "Description",
            "isInlineImage": true,
            "imageWidth": 1600,
            "imageHeight": 900
          },
          "showDescription": true,
          "showTitle": true,
          "alternateText": ""
        }
      ]
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {
        "slides[0].title": "Tile Title",
        "slides[0].description": "Description text"
      },
      "imageSources": {
        "slides[0].thumbnail.imageSource": "/sites/mysite/SiteAssets/hero.jpg"
      },
      "links": {
        "slides[0].url": "https://example.com"
      }
    }
  }
}
```

### Quick Links
- **webPartId:** `c70391ea-0b10-4ee9-b2b4-006d3fcad0cd`
- **alias:** `QuickLinksWebPart`
- **Layouts:** `"Button"`, `"CompactCard"`, `"FilmStrip"`, `"Grid"`, `"List"`, `"Tiles"`

```json
{
  "controlType": 3,
  "webPartId": "c70391ea-0b10-4ee9-b2b4-006d3fcad0cd",
  "webPartData": {
    "id": "c70391ea-0b10-4ee9-b2b4-006d3fcad0cd",
    "instanceId": "<guid>",
    "title": "Quick links",
    "dataVersion": "2.2",
    "properties": {
      "items": [
        {
          "sourceItem": {
            "itemType": 2,
            "fileExtension": "",
            "progId": ""
          },
          "thumbnailType": 2,
          "id": 1,
          "description": "Link description",
          "fabricIconProps": {
            "codepoint": 59530,
            "fontFace": "FabricMDL2Icons"
          }
        }
      ],
      "isMigrated": true,
      "layoutId": "CompactCard",
      "shouldShowThumbnail": true,
      "hideWebPartWhenEmpty": true
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {
        "items[0].title": "Link Title"
      },
      "imageSources": {},
      "links": {
        "items[0].sourceItem.url": "https://example.com"
      }
    }
  }
}
```

### Call to Action
- **webPartId:** `df8e44e7-edd5-46d5-90da-aca1539313b8`
- **alias:** `CallToActionWebPart`

```json
{
  "controlType": 3,
  "webPartId": "df8e44e7-edd5-46d5-90da-aca1539313b8",
  "webPartData": {
    "id": "df8e44e7-edd5-46d5-90da-aca1539313b8",
    "instanceId": "<guid>",
    "title": "Call to action",
    "dataVersion": "1.0",
    "properties": {
      "isTitleEnabled": true,
      "isSubtitleEnabled": true,
      "isImageEnabled": true,
      "isButtonEnabled": true,
      "title": "Title",
      "subtitle": "Subtitle",
      "buttonText": "Click here",
      "buttonUrl": "https://example.com",
      "buttonTarget": "_blank",
      "textAlignment": "Left"
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {
        "title": "Title",
        "subtitle": "Subtitle"
      },
      "imageSources": {},
      "links": {
        "buttonUrl": "https://example.com"
      }
    }
  }
}
```

### Button
- **webPartId:** `0f087d7f-520e-42b7-89c0-496aaf979d58`
- **alias:** `ButtonWebPart`
- **Types:** `"Primary"`, `"Secondary"`, `"Tertiary"`
- **Alignment:** `"Left"`, `"Center"`, `"Right"`

```json
{
  "controlType": 3,
  "webPartId": "0f087d7f-520e-42b7-89c0-496aaf979d58",
  "webPartData": {
    "id": "0f087d7f-520e-42b7-89c0-496aaf979d58",
    "instanceId": "<guid>",
    "title": "Button",
    "dataVersion": "1.0",
    "properties": {
      "text": "Click here",
      "url": "https://example.com",
      "buttonType": "Primary",
      "align": "Center",
      "newTab": false
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {},
      "links": { "url": "https://example.com" }
    }
  }
}
```

## Layout Web Parts

### Divider
- **webPartId:** `2161a1c6-db61-4731-b97c-3cdb303f7cbb`
- **alias:** `DividerWebPart`

```json
{
  "controlType": 3,
  "webPartId": "2161a1c6-db61-4731-b97c-3cdb303f7cbb",
  "webPartData": {
    "id": "2161a1c6-db61-4731-b97c-3cdb303f7cbb",
    "instanceId": "<guid>",
    "title": "Divider",
    "dataVersion": "1.2",
    "properties": {
      "displayShading": false,
      "lineColor": "#EAEAEA",
      "lineThickness": 1,
      "lineWidth": 100,
      "spaceAbove": 3,
      "spaceBelow": 3,
      "showLine": true
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {},
      "links": {}
    }
  }
}
```

### Spacer
- **webPartId:** `8654b779-4886-46d4-8ffb-b5ed960ee986`
- **alias:** `SpacerWebPart`

```json
{
  "controlType": 3,
  "webPartId": "8654b779-4886-46d4-8ffb-b5ed960ee986",
  "webPartData": {
    "id": "8654b779-4886-46d4-8ffb-b5ed960ee986",
    "instanceId": "<guid>",
    "title": "Spacer",
    "dataVersion": "1.0",
    "properties": {
      "height": 50
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {},
      "links": {}
    }
  }
}
```

## Data & Embed Web Parts

### Embed (iframe)
- **webPartId:** `490d7c76-1824-45b2-9de3-676421c997fa`
- **alias:** `ContentEmbedWebPart`
- **Allowed domains:** YouTube, Vimeo, Power BI, Microsoft Forms/Stream/Teams, Bing Maps

```json
{
  "controlType": 3,
  "webPartId": "490d7c76-1824-45b2-9de3-676421c997fa",
  "webPartData": {
    "id": "490d7c76-1824-45b2-9de3-676421c997fa",
    "instanceId": "<guid>",
    "title": "Embed",
    "dataVersion": "1.0",
    "properties": {
      "embedCode": "<iframe src=\"https://www.youtube.com/embed/VIDEO_ID\" width=\"560\" height=\"315\" frameborder=\"0\"></iframe>",
      "shouldScaleWidth": true
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {},
      "links": {}
    }
  }
}
```

### Highlighted Content
- **webPartId:** `daf0b71c-6de8-4ef7-b511-faae7c388708`
- **alias:** `ContentRollupWebPart`
- **Layouts:** `"Card"`, `"Carousel"`, `"Filmstrip"`, `"List"`, `"Compact"`

### News
- **webPartId:** `8c88f208-6c77-4bdb-86a0-0c47b4316588`
- **alias:** `NewsWebPart`
- **Layouts:** `"FeaturedNews"`, `"Carousel"`, `"List"`, `"Tiles"`, `"SideBySide"`, `"Cards"`

### People
- **webPartId:** `7f718435-ee4d-431c-bdbf-9c4ff326f46e`
- **alias:** `PeopleWebPart`
- **Layout:** `0` = Compact, `1` = Full card

### Events
- **webPartId:** `20745d7d-8581-4a6c-bf26-68279bc123fc`
- **alias:** `EventsWebPart`
- **Layout:** `0` = Filmstrip, `1` = Compact, `2` = Narrow

### Countdown Timer
- **webPartId:** `62cac389-787f-495d-beca-e11786162ef4`
- **alias:** `CountdownWebPart`

### Power BI
- **webPartId:** `58fcd18b-e1af-4b0a-b23b-422c2c52d5a2`
- **alias:** `PowerBIReportEmbedWebPart`

### Microsoft Forms
- **webPartId:** `b19b3b9e-8d13-4fec-a93c-401a091c0707`
- **alias:** `FormsWebPart`

### List
- **webPartId:** `f92bf067-bc19-489e-a556-7fe95f508720`
- **alias:** `ListWebPart`

### File Viewer / Document Embed
- **webPartId:** `b7dd04e1-19ce-4b24-9132-b60a1c2b910d`
- **alias:** `DocumentEmbedWebPart`

### YouTube Embed
- **webPartId:** `544dd15b-cf3c-441b-96da-004d5a8cea1d`
- **alias:** `YouTubeEmbedWebPart`

### Stream
- **webPartId:** `ac0e47ca-30af-452c-bdbb-510b715d0e46`
- **alias:** `StreamWebPart`

## Productivity Web Parts

### Markdown
- **webPartId:** `1ef5ed11-ce7b-44be-bc5e-4abd55101d16`
- **alias:** `MarkdownWebPart`

```json
{
  "webPartData": {
    "id": "1ef5ed11-ce7b-44be-bc5e-4abd55101d16",
    "instanceId": "<guid>",
    "title": "Markdown",
    "dataVersion": "1.0",
    "properties": {
      "content": "# Heading\n\nThis is **bold** and _italic_.\n\n- Item 1\n- Item 2"
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {},
      "imageSources": {},
      "links": {}
    }
  }
}
```

### Code Snippet
- **webPartId:** `7b317bca-c919-4982-af2f-8399173e5a1e`
- **alias:** `CodeSnippetWebPart`
- **Languages:** Abap, Bash, C, CPP, CSharp, CSS, Go, HTML, Java, JavaScript, Kotlin, PowerShell, Python, Ruby, SQL, TypeScript, XML, YAML
- **CRITICAL:** Replace `<` with `&lt;` in `searchablePlainTexts.code`

```json
{
  "webPartData": {
    "id": "7b317bca-c919-4982-af2f-8399173e5a1e",
    "instanceId": "<guid>",
    "title": "Code snippet",
    "dataVersion": "1.0",
    "properties": {
      "code": "const x = 42;\nconsole.log(x);",
      "language": "JavaScript",
      "showLineNumbers": true,
      "wrap": false,
      "fontFamily": "Monospace",
      "fontSize": "12",
      "theme": "Office"
    },
    "serverProcessedContent": {
      "htmlStrings": {},
      "searchablePlainTexts": {
        "code": "const x = 42;\nconsole.log(x);"
      },
      "imageSources": {},
      "links": {}
    }
  }
}
```

## Other Notable Web Parts

| Web Part | GUID | Alias |
|----------|------|-------|
| World Clock | `81b57906-cbed-4bb1-9823-2e3314f46f28` | `WorldClockWebPart` |
| Weather | `868ac3c3-cad7-4bd6-9a1c-14dc5cc8e823` | `WeatherWebPart` |
| Bing Maps | `e377ea37-9047-43b9-8cdb-a761be2f8e09` | `BingMapsWebPart` |
| Image Gallery | `af8be689-990e-492a-81f7-ba3e4cd3ed9c` | `ImageGalleryWebPart` |
| Site Activity | `eb95c819-ab8f-4689-bd03-0c2d65d47b1f` | `SiteActivityWebPart` |
| Org Chart | `e84a8ca2-f63c-4fb9-bc0b-d8eef5ccb22b` | `OrgChartWebPart` |
| Planner | `39c4c1c2-63fa-41be-8cc2-f6c0b49b253d` | `PlannerWebPart` |
| Quick Chart | `91a50c94-865f-4f5c-8b4e-e49659e69772` | `QuickChartWebPart` |
| FAQ | `481a605c-a625-487f-b731-96568350430c` | `FaqWebPart` |
| Yammer Feed | `cb3bfe97-a47f-47ca-bffb-bb9a5ff83d75` | `YammerFullFeedWebPart` |
| Power App | `9d7e898c-f1bb-473a-9ace-8b415036578b` | `PowerAppPlayerWebPart` |
| Sites | `7cba020c-5ccb-42e8-b6fc-75b3149aba7b` | `SitesWebPart` |
| Link Preview | `6410b3b6-d440-4663-8744-378976dc041e` | `LinkPreviewWebPart` |
| Courses | `df851228-e2ea-407c-8d93-22e4617118ca` | `CoursesWebPart` |
| Editorial Card | `90c0a746-fdcd-4b85-9e6b-52528adc8b10` | `EditorialCardWebPart` |

## Corrected GUIDs (Research vs. Tenant)

These GUIDs differed from general documentation:

| Web Part | Research GUID | Actual Tenant GUID |
|----------|--------------|-------------------|
| Divider | `2161a1c6-...-a1d6709de63b` | `2161a1c6-...-3cdb303f7cbb` |
| Power BI | `58fcd18b-...-422c2c364d64` | `58fcd18b-...-422c2c52d5a2` |
| Highlighted Content | `e377ea37-...` | `daf0b71c-6de8-4ef7-b511-faae7c388708` (ContentRollupWebPart) |
| Forms | `b19d5b37-...` | `b19b3b9e-8d13-4fec-a93c-401a091c0707` |
| File Viewer | `22a6f4f9-...` | `b7dd04e1-19ce-4b24-9132-b60a1c2b910d` (DocumentEmbedWebPart) |

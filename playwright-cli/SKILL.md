---
name: playwright-cli
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, test web applications, or extract information from web pages.
allowed-tools: Bash(playwright-cli:*)
---

# Browser Automation with playwright-cli

Always invoke the CLI with `npx playwright-cli ...`. Do not use bare `playwright-cli ...`, because the global binary may not be installed in the workspace.

Default browser policy for this skill:

- Prefer Lightpanda first for fresh browser work
- Reuse `127.0.0.1:9222` only when the CDP endpoint clearly identifies itself as Lightpanda
- If Lightpanda is installed but not running, start it locally and attach via Playwright CLI config
- If Lightpanda is missing, unhealthy, or attach fails, say that you are continuing with Chrome and use `--browser=chrome`

When you need a fresh browser session, use this decision order:

1. Try `http://127.0.0.1:9222/json/version` and reuse it only if the response clearly looks like Lightpanda.
2. Otherwise resolve the binary in this order: `LIGHTPANDA_BIN`, `command -v lightpanda`, `~/.local/bin/lightpanda`, `/usr/local/bin/lightpanda`, `/opt/homebrew/bin/lightpanda`.
3. If a binary is available, start `lightpanda serve --host 127.0.0.1 --port 9222`, read `webSocketDebuggerUrl` from `/json/version`, and pass it to Playwright CLI through a temporary config file.
4. If any step fails, tell the user in one short sentence and continue with Chrome.

Use this Lightpanda-first setup when you need a new browser:

```bash
# Reuse or start Lightpanda, then attach Playwright CLI through CDP.
# Only reuse an existing endpoint when /json/version clearly identifies it as Lightpanda.

LIGHTPANDA_BIN="${LIGHTPANDA_BIN:-$(command -v lightpanda 2>/dev/null || true)}"

if curl -fsS http://127.0.0.1:9222/json/version >/tmp/lightpanda-version.json 2>/dev/null; then
  :
elif [ -n "$LIGHTPANDA_BIN" ]; then
  "$LIGHTPANDA_BIN" serve --host 127.0.0.1 --port 9222 >/tmp/lightpanda.log 2>&1 &
  sleep 2
  curl -fsS http://127.0.0.1:9222/json/version >/tmp/lightpanda-version.json
fi

node -e "const fs=require('fs'); const version=JSON.parse(fs.readFileSync('/tmp/lightpanda-version.json','utf8')); if (!version.webSocketDebuggerUrl) process.exit(1); fs.writeFileSync('/tmp/playwright-lightpanda.json', JSON.stringify({ browser: { cdpEndpoint: version.webSocketDebuggerUrl, cdpTimeout: 30000 } }, null, 2));"

npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com
```

Chrome fallback:

```bash
# Example fallback message: "Lightpanda is not available here, so I'm continuing with Chrome."
npx playwright-cli open https://example.com --browser=chrome
```

## Quick start

```bash
# open new browser
npx playwright-cli open
# navigate to a page
npx playwright-cli goto https://playwright.dev
# interact with the page using refs from the snapshot
npx playwright-cli click e15
npx playwright-cli type "page.click"
npx playwright-cli press Enter
# take a screenshot
npx playwright-cli screenshot
# close the browser
npx playwright-cli close
```

## Commands

### Core

```bash
npx playwright-cli open
# open and navigate right away
npx playwright-cli open https://example.com/
npx playwright-cli goto https://playwright.dev
npx playwright-cli type "search query"
npx playwright-cli click e3
npx playwright-cli dblclick e7
npx playwright-cli fill e5 "user@example.com"
npx playwright-cli drag e2 e8
npx playwright-cli hover e4
npx playwright-cli select e9 "option-value"
npx playwright-cli upload ./document.pdf
npx playwright-cli check e12
npx playwright-cli uncheck e12
npx playwright-cli snapshot
npx playwright-cli snapshot --filename=after-click.yaml
npx playwright-cli eval "document.title"
npx playwright-cli eval "el => el.textContent" e5
npx playwright-cli dialog-accept
npx playwright-cli dialog-accept "confirmation text"
npx playwright-cli dialog-dismiss
npx playwright-cli resize 1920 1080
npx playwright-cli close
```

### Navigation

```bash
npx playwright-cli go-back
npx playwright-cli go-forward
npx playwright-cli reload
```

### Keyboard

```bash
npx playwright-cli press Enter
npx playwright-cli press ArrowDown
npx playwright-cli keydown Shift
npx playwright-cli keyup Shift
```

### Mouse

```bash
npx playwright-cli mousemove 150 300
npx playwright-cli mousedown
npx playwright-cli mousedown right
npx playwright-cli mouseup
npx playwright-cli mouseup right
npx playwright-cli mousewheel 0 100
```

### Save as

```bash
npx playwright-cli screenshot
npx playwright-cli screenshot e5
npx playwright-cli screenshot --filename=page.png
npx playwright-cli pdf --filename=page.pdf
```

### Tabs

```bash
npx playwright-cli tab-list
npx playwright-cli tab-new
npx playwright-cli tab-new https://example.com/page
npx playwright-cli tab-close
npx playwright-cli tab-close 2
npx playwright-cli tab-select 0
```

### Storage

```bash
npx playwright-cli state-save
npx playwright-cli state-save auth.json
npx playwright-cli state-load auth.json

# Cookies
npx playwright-cli cookie-list
npx playwright-cli cookie-list --domain=example.com
npx playwright-cli cookie-get session_id
npx playwright-cli cookie-set session_id abc123
npx playwright-cli cookie-set session_id abc123 --domain=example.com --httpOnly --secure
npx playwright-cli cookie-delete session_id
npx playwright-cli cookie-clear

# LocalStorage
npx playwright-cli localstorage-list
npx playwright-cli localstorage-get theme
npx playwright-cli localstorage-set theme dark
npx playwright-cli localstorage-delete theme
npx playwright-cli localstorage-clear

# SessionStorage
npx playwright-cli sessionstorage-list
npx playwright-cli sessionstorage-get step
npx playwright-cli sessionstorage-set step 3
npx playwright-cli sessionstorage-delete step
npx playwright-cli sessionstorage-clear
```

### Network

```bash
npx playwright-cli route "**/*.jpg" --status=404
npx playwright-cli route "https://api.example.com/**" --body='{"mock": true}'
npx playwright-cli route-list
npx playwright-cli unroute "**/*.jpg"
npx playwright-cli unroute
```

### DevTools

```bash
npx playwright-cli console
npx playwright-cli console warning
npx playwright-cli network
npx playwright-cli run-code "async page => await page.context().grantPermissions(['geolocation'])"
npx playwright-cli tracing-start
npx playwright-cli tracing-stop
npx playwright-cli video-start
npx playwright-cli video-stop video.webm
```

### Install

```bash
npx playwright-cli install --skills
npx playwright-cli install-browser
```

### Configuration
```bash
# Default skill path: Lightpanda first, Chrome fallback
# Use a temp config with browser.cdpEndpoint when attaching to Lightpanda

# Use specific browser when creating session
npx playwright-cli open --browser=chrome
npx playwright-cli open --browser=firefox
npx playwright-cli open --browser=webkit
npx playwright-cli open --browser=msedge
# Connect to browser via extension
npx playwright-cli open --extension

# Use persistent profile (by default profile is in-memory)
npx playwright-cli open --persistent
# Use persistent profile with custom directory
npx playwright-cli open --profile=/path/to/profile

# Start with config file
npx playwright-cli open --config=my-config.json

# Attach to Lightpanda through CDP
npx playwright-cli --config=/tmp/playwright-lightpanda.json open https://example.com

# Close the browser
npx playwright-cli close
# Delete user data for the default session
npx playwright-cli delete-data
```

### Browser Sessions

```bash
# create new browser session named "mysession" with persistent profile
npx playwright-cli -s=mysession open example.com --persistent
# same with manually specified profile directory (use when requested explicitly)
npx playwright-cli -s=mysession open example.com --profile=/path/to/profile
npx playwright-cli -s=mysession click e6
npx playwright-cli -s=mysession close  # stop a named browser
npx playwright-cli -s=mysession delete-data  # delete user data for persistent session

npx playwright-cli list
# Close all browsers
npx playwright-cli close-all
# Forcefully kill all browser processes
npx playwright-cli kill-all
```

## Example: Form submission

```bash
# Preferred path when Lightpanda is available
npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com/form
npx playwright-cli snapshot

npx playwright-cli fill e1 "user@example.com"
npx playwright-cli fill e2 "password123"
npx playwright-cli click e3
npx playwright-cli snapshot
npx playwright-cli close
```

## Example: Multi-tab workflow

```bash
npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com
npx playwright-cli tab-new https://example.com/other
npx playwright-cli tab-list
npx playwright-cli tab-select 0
npx playwright-cli snapshot
npx playwright-cli close
```

## Example: Debugging with DevTools

```bash
npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com
npx playwright-cli click e4
npx playwright-cli fill e7 "test"
npx playwright-cli console
npx playwright-cli network
npx playwright-cli close
```

```bash
npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com
npx playwright-cli tracing-start
npx playwright-cli click e4
npx playwright-cli fill e7 "test"
npx playwright-cli tracing-stop
npx playwright-cli close
```

## Specific tasks

* **Request mocking** [references/request-mocking.md](references/request-mocking.md)
* **Running Playwright code** [references/running-code.md](references/running-code.md)
* **Browser session management** [references/session-management.md](references/session-management.md)
* **Storage state (cookies, localStorage)** [references/storage-state.md](references/storage-state.md)
* **Test generation** [references/test-generation.md](references/test-generation.md)
* **Tracing** [references/tracing.md](references/tracing.md)
* **Video recording** [references/video-recording.md](references/video-recording.md)
* **Lightpanda-first browser setup** [references/session-management.md](references/session-management.md#lightpanda-first-sessions)

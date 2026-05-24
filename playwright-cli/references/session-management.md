# Browser Session Management

Run multiple isolated browser sessions concurrently with state persistence.

## Named Browser Sessions

Use `-b` flag to isolate browser contexts:

```bash
# Browser 1: Authentication flow
npx playwright-cli -s=auth open https://app.example.com/login

# Browser 2: Public browsing (separate cookies, storage)
npx playwright-cli -s=public open https://example.com

# Commands are isolated by browser session
npx playwright-cli -s=auth fill e1 "user@example.com"
npx playwright-cli -s=public snapshot
```

## Browser Session Isolation Properties

Each browser session has independent:
- Cookies
- LocalStorage / SessionStorage
- IndexedDB
- Cache
- Browsing history
- Open tabs

## Browser Session Commands

```bash
# List all browser sessions
npx playwright-cli list

# Stop a browser session (close the browser)
npx playwright-cli close                # stop the default browser
npx playwright-cli -s=mysession close   # stop a named browser

# Stop all browser sessions
npx playwright-cli close-all

# Forcefully kill all daemon processes (for stale/zombie processes)
npx playwright-cli kill-all

# Delete browser session user data (profile directory)
npx playwright-cli delete-data                # delete default browser data
npx playwright-cli -s=mysession delete-data   # delete named browser data
```

## Environment Variable

Set a default browser session name via environment variable:

```bash
export PLAYWRIGHT_CLI_SESSION="mysession"
npx playwright-cli open example.com  # Uses "mysession" automatically
```

## Lightpanda-first Sessions

This skill now prefers Lightpanda for new browser work, with Chrome as the fallback.

Use this order:

1. Check `http://127.0.0.1:9222/json/version`
2. Reuse that endpoint only when it clearly identifies itself as Lightpanda
3. Otherwise resolve `lightpanda` from `LIGHTPANDA_BIN`, `PATH`, `~/.local/bin/lightpanda`, `/usr/local/bin/lightpanda`, or `/opt/homebrew/bin/lightpanda`
4. Start `lightpanda serve --host 127.0.0.1 --port 9222`
5. Read `webSocketDebuggerUrl` from `/json/version`
6. Write a temporary Playwright CLI config with `browser.cdpEndpoint`
7. If any step fails, continue with Chrome instead of blocking the task

### Lightpanda attach flow

```bash
curl -fsS http://127.0.0.1:9222/json/version >/tmp/lightpanda-version.json

node -e "const fs=require('fs'); const version=JSON.parse(fs.readFileSync('/tmp/lightpanda-version.json','utf8')); fs.writeFileSync('/tmp/playwright-lightpanda.json', JSON.stringify({ browser: { cdpEndpoint: version.webSocketDebuggerUrl, cdpTimeout: 30000 } }, null, 2));"

npx playwright-cli --config /tmp/playwright-lightpanda.json open https://example.com
```

Config shape:

```json
{
  "browser": {
    "cdpEndpoint": "ws://127.0.0.1:9222/devtools/browser/<id>",
    "cdpTimeout": 30000
  }
}
```

### Chrome fallback

Use Chrome when Lightpanda is missing, the port is occupied by a non-Lightpanda process, startup fails, or Playwright CLI cannot attach.

```bash
npx playwright-cli open https://example.com --browser=chrome
```

## Common Patterns

### Concurrent Scraping

```bash
#!/bin/bash
# Scrape multiple sites concurrently

# Start all browsers
npx playwright-cli -s=site1 open https://site1.com &
npx playwright-cli -s=site2 open https://site2.com &
npx playwright-cli -s=site3 open https://site3.com &
wait

# Take snapshots from each
npx playwright-cli -s=site1 snapshot
npx playwright-cli -s=site2 snapshot
npx playwright-cli -s=site3 snapshot

# Cleanup
npx playwright-cli close-all
```

### A/B Testing Sessions

```bash
# Test different user experiences
npx playwright-cli -s=variant-a open "https://app.com?variant=a"
npx playwright-cli -s=variant-b open "https://app.com?variant=b"

# Compare
npx playwright-cli -s=variant-a screenshot
npx playwright-cli -s=variant-b screenshot
```

### Persistent Profile

By default, browser profile is kept in memory only. Use `--persistent` flag on `open` to persist the browser profile to disk:

```bash
# Use persistent profile (auto-generated location)
npx playwright-cli open https://example.com --persistent

# Use persistent profile with custom directory
npx playwright-cli open https://example.com --profile=/path/to/profile
```

## Default Browser Session

When `-s` is omitted, commands use the default browser session:

```bash
# These use the same default browser session
npx playwright-cli open https://example.com
npx playwright-cli snapshot
npx playwright-cli close  # Stops default browser
```

## Browser Session Configuration

Configure a browser session with specific settings when opening:

```bash
# Open with config file
npx playwright-cli open https://example.com --config=.playwright/my-cli.json

# Open with specific browser
npx playwright-cli open https://example.com --browser=firefox

# Open in headed mode
npx playwright-cli open https://example.com --headed

# Open with persistent profile
npx playwright-cli open https://example.com --persistent
```

## Best Practices

### 1. Name Browser Sessions Semantically

```bash
# GOOD: Clear purpose
npx playwright-cli -s=github-auth open https://github.com
npx playwright-cli -s=docs-scrape open https://docs.example.com

# AVOID: Generic names
npx playwright-cli -s=s1 open https://github.com
```

### 2. Always Clean Up

```bash
# Stop browsers when done
npx playwright-cli -s=auth close
npx playwright-cli -s=scrape close

# Or stop all at once
npx playwright-cli close-all

# If browsers become unresponsive or zombie processes remain
npx playwright-cli kill-all
```

### 3. Delete Stale Browser Data

```bash
# Remove old browser data to free disk space
npx playwright-cli -s=oldsession delete-data
```

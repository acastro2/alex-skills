# Video Recording

Capture browser automation sessions as video for debugging, documentation, or verification. Produces WebM (VP8/VP9 codec).

## Basic Recording

```bash
# Start recording
npx playwright-cli video-start

# Perform actions
npx playwright-cli open https://example.com
npx playwright-cli snapshot
npx playwright-cli click e1
npx playwright-cli fill e2 "test input"

# Stop and save
npx playwright-cli video-stop demo.webm
```

## Best Practices

### 1. Use Descriptive Filenames

```bash
# Include context in filename
npx playwright-cli video-stop recordings/login-flow-2024-01-15.webm
npx playwright-cli video-stop recordings/checkout-test-run-42.webm
```

## Tracing vs Video

| Feature | Video | Tracing |
|---------|-------|---------|
| Output | WebM file | Trace file (viewable in Trace Viewer) |
| Shows | Visual recording | DOM snapshots, network, console, actions |
| Use case | Demos, documentation | Debugging, analysis |
| Size | Larger | Smaller |

## Limitations

- Recording adds slight overhead to automation
- Large recordings can consume significant disk space

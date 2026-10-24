# Project tools

`setup.ps1` installs and builds the local application; `start.ps1` applies migrations and starts it. `configure_vercel.py` writes the public Oracle HTTPS destination into the frontend deployment configuration. See [deployment](../DEPLOYMENT.md) before using it.

The tools below maintain the versioned SDLC baselines. `manual_qa_server.py` is an optional isolated local server helper; it does not by itself perform a manual audit. The current increment uses automated checks at the user's request.

The root lockfile pins Mermaid CLI and Puppeteer. A scoped KaTeX override selects 0.18.10 to avoid advisory GHSA-238p-pmpm-9mq7 in the CLI's older dependency range; the diagram set is rendered to verify compatibility. Recheck the override when upgrading the CLI.

## Check documentation

```powershell
python scripts/check_docs.py
```

Checks relative Markdown file links and captured-baseline file inventories/SHA-256 hashes. It deliberately does not verify external websites, Markdown fragment anchors, model availability, or application behavior.

## Render Mermaid diagrams

Use Node.js 24 and the pinned root `package-lock.json`. Install the documentation dependencies with `npm ci`. To use an existing open-source Chromium installation without downloading Puppeteer's default browser, set `PUPPETEER_SKIP_DOWNLOAD=true` during installation and set `PUPPETEER_EXECUTABLE_PATH` to the Chromium executable when rendering. The browser runs headlessly with a temporary profile.

```powershell
# Set this to the Chromium executable installed on your machine.
$env:PUPPETEER_EXECUTABLE_PATH = 'C:/path/to/chromium.exe'
npm run docs:render -- v0.1.0 .local/diagram-check/v0.1.0
```

For an uncaptured draft version only, omit the output path to save SVGs beside their `.mmd` sources. The renderer refuses to overwrite files inside a captured baseline. Use the separate output path for later verification; SVG serialization can vary across browser/font versions, so a rerender is a syntax/renderability check rather than a byte-identical baseline assertion.

On this workstation, an existing Playwright Chromium headless-shell installation was used. Its machine-specific path is deliberately not hardcoded into the reusable script. No public rendering service is required.

## Capture a completed baseline

```powershell
python scripts/capture_baseline.py doc/v0.1.0 --date 2026-10-24
python scripts/check_docs.py
```

Supply the actual client-local date and a new version. Capture refuses to replace an existing manifest. It hashes baseline files, not the manifest itself. These hashes detect later changes; they are not a cryptographic signature or proof of academic approval.

# BPKH Governance Contagion — Synthetic Remote Update Demo

This package is for a **technical PWA update demonstration only**. It is not a new research release.

## What changes
Only the latest monthly row (`2026-09`) in the demo dataset is intentionally changed:
- NCI: `0.742`
- Anomaly: `0.880`
- EWS: `0.812` — `RED`
- GCR: `0.784` — `RED`

All other analytical records are copied from the frozen research snapshot.

## Upload to GitHub
Upload/replace the following at the repository root:
- `manifest.json` (temporary demo manifest)
- `releases/2026.09.24-DEMO/manifest.json`
- `releases/2026.09.24-DEMO/pwa_data.json`

Keep the existing `releases/2026.09.03/` release unchanged.

## Expected PWA behavior
After refresh, the PWA should show the remote dataset version `2026.09.24-DEMO` and the latest analytical signal should change from the research snapshot's GREEN state to RED.

## IMPORTANT
After demonstrating the update, restore the root `manifest.json` so that it points back to `2026.09.03`. The DEMO release can remain in GitHub as a clearly labeled technical test release, or be removed after testing.

Do not cite `2026.09.24-DEMO` as a research result.

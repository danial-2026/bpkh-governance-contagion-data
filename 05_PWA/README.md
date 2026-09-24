# BPKH Governance Contagion EWS PWA v0.4

Institutional research prototype with a versioned data layer. The v0.2 visual design is frozen; v0.4 separates the frontend from the analytical dataset so compatible data can be updated without rebuilding the frontend.

## Run locally

Requirements: Node.js 18+ and npm. On Windows PowerShell, if `npm` is blocked by script execution policy, use `npm.cmd`.

```bash
npm.cmd install
npm.cmd run dev
```

Then open the local URL shown by Vite (normally http://localhost:5173).

For a production build:

```bash
npm.cmd run build
npm.cmd run preview
```

## Data architecture

The application reads `/data/manifest.json` first. The manifest identifies the dataset version and points to a versioned JSON dataset under `/data/releases/<version>/`. If the manifest or current dataset is unavailable, the application falls back to `/data/pwa_data.json` so the research snapshot remains usable offline.

The service worker uses a network-first strategy for JSON data. This allows a reachable newer manifest/dataset to replace the cached snapshot without changing the frontend, while retaining an offline copy after it has been cached.

## Current dataset

- Dataset ID: `bpkh-governance-contagion`
- Version: `2026.09.03`
- Status: `research_snapshot`
- Analytical status: `frozen`
- Observation period: `2024-01-01` to `2026-09-03`

## Updating the dataset

1. Add a compatible versioned dataset under `public/data/releases/<new-version>/pwa_data.json`.
2. Update `public/data/manifest.json` to point `dataset_path` to the new version.
3. Keep `fallback_path` pointed to a known-good snapshot.
4. Preserve `schema_version` and the existing data contract unless a deliberate frontend/schema upgrade is made.

This architecture is designed for research-to-practice transition. It does not yet implement authentication, a database, an admin panel, or a live analytical pipeline.

## Responsible interpretation

The PWA is an analytical decision-support interface. It is not an official BPKH risk rating, a corruption detector, a probability of misconduct, or evidence of causal risk transmission.


## Step 5B — GitHub remote data layer

The PWA now prefers the versioned dataset published in the GitHub repository `danial-2026/bpkh-governance-contagion-data`. The root `manifest.json` resolves the current release without requiring a frontend redeploy.

Load order:
1. Remote GitHub manifest + versioned release (`REMOTE · GITHUB`)
2. Last-known-good remote dataset cached in the browser (`CACHED REMOTE`)
3. Local versioned research snapshot (`LOCAL FALLBACK`)
4. Local root snapshot as final fallback

The UI and analytical values are unchanged from v0.3. This release changes only the data-loading architecture.

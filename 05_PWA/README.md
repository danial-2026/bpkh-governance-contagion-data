# BPKH Governance Intelligence Data Layer

This folder is the PWA data layer. The frontend reads `manifest.json` first, then loads the dataset path declared in the manifest.

## Current snapshot

- Dataset ID: `bpkh-governance-contagion`
- Version: `2026.09.03`
- Status: `research_snapshot`
- Analytical status: `frozen`
- Observation period: `2024-01-01` to `2026-09-03`

## Update principle

To publish a new compatible dataset without redeploying the frontend:

1. Add a new versioned dataset under `data/releases/<version>/pwa_data.json`.
2. Update `data/manifest.json` so `dataset_path` points to the new version.
3. Keep `fallback_path` pointing to a known-good local snapshot.
4. Preserve the same dataset contract unless the frontend and schema version are intentionally upgraded.

The service worker uses a network-first strategy for JSON data so a reachable newer manifest/dataset can replace the cached research snapshot, while the cached copy remains available when offline.

Do not publish raw platform-restricted or personally identifying social-media records through this public PWA data layer.

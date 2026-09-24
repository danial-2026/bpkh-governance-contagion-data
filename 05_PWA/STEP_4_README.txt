STEP 4 — DATA UPDATE ARCHITECTURE

Implemented in PWA v0.3:
1. Data manifest: public/data/manifest.json
2. Versioned research snapshot: public/data/releases/2026.09.03/pwa_data.json
3. Fallback snapshot: public/data/pwa_data.json
4. Frontend data loader: src/dataLayer.js
5. PWA JSON runtime caching: NetworkFirst with offline fallback
6. UI dataset/version status indicator
7. Documentation in public/data/README.md

Operational principle:
- The frontend loads the manifest first.
- The manifest points to the current versioned dataset.
- If the manifest/current dataset is unavailable, the app falls back to the known-good snapshot.
- A future compatible dataset can be published by adding a new version and updating manifest.json; the frontend does not need to be rebuilt.

Current status:
Research snapshot / frozen / 2024-01-01 to 2026-09-03.

Not included yet:
- live scraping
- database
- authentication
- admin panel
- automated analytical pipeline


STEP 5B — GITHUB REMOTE DATA LAYER
- Remote source: danial-2026/bpkh-governance-contagion-data
- Load priority: GitHub remote -> cached remote -> local versioned snapshot -> local root snapshot.
- Frontend code does not change when a compatible dataset release changes.
- UI remains frozen; only data-loading architecture changed in v0.4.

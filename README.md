# BPKH Governance Contagion — Remote Data Layer

Versioned static data repository for the **BPKH Governance Contagion Early-Warning System (EWS)** PWA.

## Purpose

This repository separates the analytical dataset from the PWA frontend. The PWA can consume a versioned `manifest.json` and dataset without embedding analytical values in the application code.

The repository is intended for the current **research snapshot** and future versioned releases. It does not contain raw social-media data or other restricted source material.

## Current release

- Dataset: `bpkh-governance-contagion`
- Version: `2026.09.03`
- Status: `research_snapshot`
- Analytical status: `frozen`
- Observation period: `2024-01-01` to `2026-09-03`

## Repository structure

```text
.
├── manifest.json
├── pwa_data.json
├── releases/
│   └── 2026.09.03/
│       ├── manifest.json
│       └── pwa_data.json
└── README.md
```

`manifest.json` at the repository root is the stable entry point for the PWA. The root manifest points to the current release dataset. Each release directory is retained for reproducibility and rollback.

## Update protocol

For a new analytical release:

1. Create a new release directory, e.g. `releases/2026.10.01/`.
2. Add the new `pwa_data.json`.
3. Add the corresponding release `manifest.json`.
4. Update the root `manifest.json` so `dataset_version`, `dataset_path`, `last_updated`, and observation metadata point to the new release.
5. Keep previous releases unchanged.
6. Validate the JSON before publishing.
7. Commit the release with a descriptive message.

The PWA frontend does not need to change when only the dataset release changes.

## Important interpretation note

The dataset contains analytical decision-support signals from the BPKH Governance Contagion research framework. It is not an official BPKH risk rating, corruption detector, probability of misconduct, or causal estimate of risk transmission.

## Data governance

This repository is designed for aggregated and derived research outputs. Raw platform data, personal data, credentials, API tokens, and restricted source material should not be committed here.

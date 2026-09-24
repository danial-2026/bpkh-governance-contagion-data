# Data Dictionary

## `pwa_data.json`

The current release packages the analytical datasets used by the PWA:

- `monthly_ews`: monthly NCI, anomaly score, EWS, and GCR signals.
- `risk_dimensions`: prevalence and mean semantic scores for the seven guided risk dimensions.
- `network_nodes`: node-level network and NCI indicators.
- `network_edges`: observed risk-dimension co-occurrence relationships.
- `contagion_events`: detected temporal contagion episodes and component scores.
- `lag_analysis`: external-crisis lead-lag associations.

## `manifest.json`

| Field | Meaning |
|---|---|
| `dataset_id` | Stable dataset identifier |
| `dataset_version` | Current analytical release/version |
| `schema_version` | Data-contract version |
| `status` | Dataset lifecycle status, e.g. `research_snapshot` |
| `analytical_status` | Whether the analytical release is frozen |
| `observation_start` | Start of observation period |
| `observation_end` | End of observation period |
| `last_updated` | Date of dataset release/update |
| `source_label` | Human-readable research source label |
| `dataset_path` | Relative path to the current dataset |
| `fallback_path` | Relative path used for local fallback |

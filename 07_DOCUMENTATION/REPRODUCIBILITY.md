# Reproducibility

1. Obtain or generate the news corpus using the supplied news collector or a compatible BPKH/user-provided corpus.
2. Place the local master at `data_input/bpkh_news_master.csv` or set `BPKH_NEWS_MASTER`.
3. Run `02_audit_clean_news.py`.
4. Run the final news-only governance-contagion script.
5. Run the network/EWS script using the document-level and monthly outputs.
6. Compare generated outputs with the frozen `2026.09.03` release.

Exact thresholds and weights are recorded in the final scripts and manifests. Reproduction may vary if source pages change, URLs become unavailable, or external libraries/models change.

No credentials are required by the supplied news collector. If BPKH adds an authenticated data source, credentials should be provided through environment variables or a local secret manager and never committed.

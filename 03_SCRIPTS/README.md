# Analytical scripts

This repository uses **news data only**. Social-media collection, social-media cleaning, and social-media analysis have been intentionally removed from the public research toolkit.

## Recommended pipeline
1. `data_collection/01_collect_news.py` — collect candidate news from the eight defined Indonesian outlets.
2. `preprocessing/02_audit_clean_news.py` — validate dates/text, normalize duplicates, and create the clean news corpus.
3. `semantic_mapping/06_governance_contagion_intelligence_news_only.py` — final guided semantic mapping, document-level contagion scoring, event episodes, monthly GCI/SEI, anomaly detection, EWS, and lag analysis.
4. `network_analysis/07_network_cooccurrence_ews.py` — co-occurrence network, centrality, NCI, temporal network signals, AI-based EWS, and integrated GCR.

## Diagnostic/legacy scripts
`03_lexical_relevance_diagnostic.py`, `04_descriptive_news.py`, and `05_baseline_news.py` are supporting/diagnostic utilities. They are not the source of the final reported semantic taxonomy or final EWS outputs.

## BPKH/user inputs
Scripts never contain personal absolute paths or API credentials. Put local inputs under `data_input/` or set the documented environment variables. Do not commit raw article content, credentials, or private files.

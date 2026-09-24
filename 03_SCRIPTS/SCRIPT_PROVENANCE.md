# Script provenance

The seven uploaded scripts were reviewed and sanitized for this public package.

- `1a. Scrapping Raw News Data(1).py` → `01_collect_news.py`
- `2. Data Audit & Cleaning(1).py` → `02_audit_clean_news.py` (news-only rewrite)
- `3. Klasifikasi Relevansi dan Risiko(1).py` → `03_lexical_relevance_diagnostic.py` (news-only diagnostic)
- `4. Deskriptif & Visualisasi Awal(1).py` → `04_descriptive_news.py` (news-only rewrite)
- `5. Baseline Governance Analysis.py` → `05_baseline_news.py` (news-only rewrite)
- `6. Topic Modelling(6).py` → `06_governance_contagion_intelligence_news_only.py` (final guided semantic/event/GCI/SEI/EWS pipeline, social branch removed)
- `7. Network & Co-occurrence Analysis(3).py` → `07_network_cooccurrence_ews.py`

The supplied Script 6 is labeled “Topic Modelling” by filename, but its final code implements guided semantic mapping, event-aware GCI, monthly temporal analysis, anomaly detection, EWS, and lag analysis. The public package therefore renames it according to its actual analytical function.

The lexical relevance script and early descriptive/baseline scripts are retained as diagnostics, not as the final source of the reported semantic taxonomy.

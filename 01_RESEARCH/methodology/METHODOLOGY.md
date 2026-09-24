# Methodology summary

## 3.1 Research design
A quantitative text-as-data design converts public news narratives into measurable governance-risk signals. The framework is designed for detection and monitoring rather than causal prediction.

## 3.2 Data sources and corpus construction
The corpus consists of news from eight Indonesian outlets: Tempo.co, Kontan.co.id, Bisnis.com, CNBC Indonesia, Kompas.com, Detik.com, Republika.co.id, and Liputan6.com. Observation period: 1 January 2024–3 September 2026. The final analytical news corpus contains 561 documents.

## 3.3 Preprocessing and relevance filtering
Cleaning includes text/date validation, URL normalization, duplicate detection using normalized URLs and SHA-256 content hashes, and a structured relevance gate. The analytical corpus is determined by substantive relevance and data-quality controls rather than generic keyword matching.

## 3.4 Guided semantic risk mapping
Seven dimensions are used: Quota Governance, Corruption/Investigation, Governance Oversight, BPKH Governance, Hajj Fund Management, Public Trust/Reputation, and Clarification/Response. Semantic representation uses `paraphrase-multilingual-MiniLM-L12-v2`. Operational similarity threshold = 0.42, margin threshold = 0.025, maximum four dimensions per document. These thresholds are study-specific design parameters, not literature constants.

## 3.5 Governance contagion, network, and event analysis
GCI is the geometric mean of External Crisis, BPKH Exposure, and Public Trust/Reputation components. Network nodes are risk dimensions; co-occurrence within a document forms edges. NCI combines centrality, crisis-edge strength, trust-edge strength, and betweenness using transparent study-specific weights. Event episodes use a seven-day window and a three-dimensional risk-profile cosine threshold of 0.72.

## 3.6 Temporal analysis, anomaly detection, and EWS
Monthly GCI, external-crisis, BPKH-exposure, public-trust, network, and NCI signals are monitored with a three-month rolling baseline. Lead-lag correlations are examined at lags 0–3 months and interpreted as temporal associations, not causality. Isolation Forest is used for unsupervised anomaly detection. The EWS combines temporal risk, NCI, and anomaly signals; GCR combines GCI, NCI, and anomaly signals. Warning thresholds use the 75th and 90th percentiles of observed scores. AI-based refers primarily to machine-learning-assisted semantic representation and unsupervised anomaly detection integrated with transparent risk rules and network indicators.

## 3.7 Robustness, reproducibility, and ethics
All public analytical outputs use versioned releases. Raw news content is not redistributed in this repository. Social-media data are excluded from this release. Study-specific thresholds and weights are documented as analytical design parameters.

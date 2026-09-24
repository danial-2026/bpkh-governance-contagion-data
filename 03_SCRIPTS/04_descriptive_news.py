"""Descriptive analysis for the NEWS corpus only.
The social-media pipeline has been intentionally removed from this research package.
"""
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

INPUT_CSV=Path(os.getenv("BPKH_ANNOTATED_NEWS", "data_input/master_auto_annotated_news.csv"))
OUT_DIR=Path(os.getenv("BPKH_DESCRIPTIVE_DIR", "04_RESULTS/descriptive")); OUT_DIR.mkdir(parents=True,exist_ok=True)

if __name__=='__main__':
    if not INPUT_CSV.exists(): raise FileNotFoundError(f"Input not found: {INPUT_CSV}. BPKH/user must supply the news dataset.")
    df=pd.read_csv(INPUT_CSV,sep=';',engine='python',on_bad_lines='skip')
    summary=df['auto_relevance'].value_counts().rename_axis('relevance').reset_index(name='document_count') if 'auto_relevance' in df.columns else pd.DataFrame()
    if not summary.empty: summary.to_csv(OUT_DIR/'news_relevance_distribution.csv',sep=';',index=False)
    if 'auto_risk_dimension' in df.columns:
        risk=df['auto_risk_dimension'].value_counts().rename_axis('risk_dimension').reset_index(name='document_count')
        risk.to_csv(OUT_DIR/'news_risk_dimensions.csv',sep=';',index=False)
        ax=risk.head(10).sort_values('document_count').plot(kind='barh',x='risk_dimension',y='document_count',legend=False,figsize=(8,5))
        ax.set_title('News Corpus Risk-Dimension Distribution'); ax.set_xlabel('Documents'); ax.set_ylabel('Risk dimension'); plt.tight_layout(); plt.savefig(OUT_DIR/'news_risk_dimensions.png',dpi=250); plt.close()
    print(f"Descriptive outputs written to {OUT_DIR.resolve()}")

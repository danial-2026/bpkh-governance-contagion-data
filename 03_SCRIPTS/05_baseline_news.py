"""Baseline monthly news-volume and source analysis. News only."""
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

INPUT_CSV=Path(os.getenv("BPKH_ANNOTATED_NEWS", "data_input/master_auto_annotated_news.csv"))
OUT_DIR=Path(os.getenv("BPKH_BASELINE_DIR", "04_RESULTS/baseline")); OUT_DIR.mkdir(parents=True,exist_ok=True)

if __name__=='__main__':
    if not INPUT_CSV.exists(): raise FileNotFoundError(f"Input not found: {INPUT_CSV}. BPKH/user must supply the news dataset.")
    df=pd.read_csv(INPUT_CSV,sep=';',engine='python',on_bad_lines='skip')
    date_col='publish_date' if 'publish_date' in df.columns else 'published_date'
    df['dt']=pd.to_datetime(df[date_col],errors='coerce',utc=True)
    monthly=df.dropna(subset=['dt']).assign(year_month=lambda x:x['dt'].dt.to_period('M').astype(str)).groupby('year_month').size().rename('News_Volume').reset_index()
    monthly.to_csv(OUT_DIR/'monthly_news_volume.csv',sep=';',index=False)
    ax=monthly.plot(x='year_month',y='News_Volume',figsize=(12,5),legend=False); ax.set_xlabel('Month'); ax.set_ylabel('Documents'); ax.set_title('Monthly News Corpus Volume'); plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(OUT_DIR/'monthly_news_volume.png',dpi=250); plt.close()
    if 'source_name' in df.columns:
        sources=df['source_name'].value_counts().rename_axis('source').reset_index(name='document_count')
        sources.to_csv(OUT_DIR/'news_source_counts.csv',sep=';',index=False)
    print(f"Baseline outputs written to {OUT_DIR.resolve()}")

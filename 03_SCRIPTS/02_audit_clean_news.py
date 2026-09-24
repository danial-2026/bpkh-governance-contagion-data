"""Audit and clean the BPKH news corpus.

No social-media data are used in this research package.
BPKH/user input: place the collected news master CSV at data_input/bpkh_news_master.csv
or set BPKH_NEWS_MASTER to an explicit local path.
"""
from __future__ import annotations
import os, re, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

START_DATE = datetime(2024,1,1,tzinfo=timezone.utc)
END_DATE = datetime(2026,9,3,23,59,59,tzinfo=timezone.utc)
INPUT_CSV = Path(os.getenv("BPKH_NEWS_MASTER", "data_input/bpkh_news_master.csv"))
OUT_DIR = Path(os.getenv("BPKH_AUDIT_DIR", "02_DATA/local_audit"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

def clean_text_basic(text):
    return re.sub(r"\s+", " ", str(text) if isinstance(text,str) else "").strip()

def compute_content_hash(text):
    return hashlib.sha256(clean_text_basic(text).lower().encode("utf-8")).hexdigest()

def audit_and_clean(csv_path):
    df=pd.read_csv(csv_path, sep=';', engine='python', on_bad_lines='skip')
    accepted=[]; rejected=[]; seen_urls=set(); seen_hashes=set()
    for _,row in df.iterrows():
        url=row.get('canonical_url') if 'canonical_url' in row and pd.notna(row.get('canonical_url')) else row.get('url')
        text=row.get('clean_content') if 'clean_content' in row and pd.notna(row.get('clean_content')) else row.get('clean_text')
        if pd.isna(text) if not isinstance(text,str) else False:
            text=row.get('raw_text','')
        date_str=row.get('publish_date') if 'publish_date' in row and pd.notna(row.get('publish_date')) else row.get('published_date')
        url=str(url) if pd.notna(url) else ''
        text=str(text) if pd.notna(text) else ''
        date_str=str(date_str) if pd.notna(date_str) else ''
        if not text or len(text.strip())<15:
            rejected.append({**row.to_dict(),'reject_reason':'MISSING_OR_TOO_SHORT_TEXT'}); continue
        try:
            dt=datetime.fromisoformat(date_str.replace('Z','+00:00'))
            if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
            if not (START_DATE<=dt<=END_DATE):
                rejected.append({**row.to_dict(),'reject_reason':'OUT_OF_BOUNDS_DATE'}); continue
        except Exception:
            rejected.append({**row.to_dict(),'reject_reason':'INVALID_DATE_FORMAT'}); continue
        clean_url=url.split('#')[0].rstrip('/') if url and url!='nan' else ''
        if clean_url and clean_url in seen_urls:
            rejected.append({**row.to_dict(),'reject_reason':'DUPLICATE_URL'}); continue
        if clean_url: seen_urls.add(clean_url)
        c_hash=compute_content_hash(text)
        if c_hash in seen_hashes:
            rejected.append({**row.to_dict(),'reject_reason':'DUPLICATE_CONTENT_HASH'}); continue
        seen_hashes.add(c_hash)
        accepted.append({**row.to_dict(),'content_hash':c_hash})
    return pd.DataFrame(accepted),pd.DataFrame(rejected)

if __name__=='__main__':
    if not INPUT_CSV.exists(): raise FileNotFoundError(f"Input not found: {INPUT_CSV}. BPKH/user must supply the news master CSV.")
    clean,rejected=audit_and_clean(INPUT_CSV)
    clean.to_csv(OUT_DIR/'news_clean.csv',sep=';',index=False,encoding='utf-8-sig')
    rejected.to_csv(OUT_DIR/'rejected.csv',sep=';',index=False,encoding='utf-8-sig')
    manifest={'news_initial':int(len(pd.read_csv(INPUT_CSV,sep=';',engine='python',on_bad_lines='skip'))),'news_clean':int(len(clean)),'rejected':int(len(rejected)),'date_start':'2024-01-01','date_end':'2026-09-03'}
    (OUT_DIR/'collection_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(manifest)

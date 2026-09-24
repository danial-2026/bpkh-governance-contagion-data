from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import re
import threading
import time
import unicodedata
import gc  # Ditambahkan untuk Garbage Collection
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urldefrag

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from langdetect import detect, LangDetectException

try:
    import trafilatura
except ImportError:
    trafilatura = None

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

try:
    # type: ignore ditambahkan agar IDE (VSCode/PyCharm) tidak rewel meski library sudah di-install
    from datasketch import MinHash, MinHashLSH  # type: ignore 
    HAS_DATASKETCH = True
except ImportError:
    HAS_DATASKETCH = False


# ============================================================
# CONFIGURATION
# ============================================================

START_DATE = datetime(2024, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2026, 9, 3, 23, 59, 59, tzinfo=timezone.utc)

WORK_DIR = Path(os.getenv("BPKH_WORK_DIR", "."))
OUT_DIR = WORK_DIR / "data_bpkh_news"
RAW_DIR = OUT_DIR / "raw"
HTML_DIR = OUT_DIR / "html"
LOG_DIR = OUT_DIR / "logs"

for d in (RAW_DIR, HTML_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

MASTER_CSV = OUT_DIR / "bpkh_news_master.csv"
MASTER_JSONL = OUT_DIR / "bpkh_news_master.jsonl"
REJECTED_CSV = OUT_DIR / "rejected.csv"

HTTP_TIMEOUT = 15
SEARCH_TIMEOUT = 20
ARTICLE_WORKERS = 10
SEARCH_WORKERS = 3

ARTICLE_DELAY = 0.15
SEARCH_DELAY = 0.5

MAX_SEARCH_RESULTS_PER_QUERY = 50
MIN_WORDS = 120

USE_SITEMAPS = os.getenv("USE_SITEMAPS", "0") == "1"
MAX_CANDIDATES_PER_SOURCE = None


# ============================================================
# SOURCES
# ============================================================

SOURCES = {
    "tempo.co": {
        "name": "Tempo",
        "domain": "tempo.co",
        "sitemaps": ["https://www.tempo.co/sitemap.xml"],
    },
    "kontan.co.id": {
        "name": "Kontan",
        "domain": "kontan.co.id",
        "sitemaps": ["https://www.kontan.co.id/sitemap.xml"],
    },
    "bisnis.com": {
        "name": "Bisnis.com",
        "domain": "bisnis.com",
        "sitemaps": ["https://www.bisnis.com/sitemap.xml"],
    },
    "cnbcindonesia.com": {
        "name": "CNBC Indonesia",
        "domain": "cnbcindonesia.com",
        "sitemaps": ["https://www.cnbcindonesia.com/sitemap.xml"],
    },
    "kompas.com": {
        "name": "Kompas.com",
        "domain": "kompas.com",
        "sitemaps": ["https://www.kompas.com/sitemap.xml"],
    },
    "detik.com": {
        "name": "Detik.com",
        "domain": "detik.com",
        "sitemaps": ["https://www.detik.com/sitemap.xml"],
    },
    "republika.co.id": {
        "name": "Republika",
        "domain": "republika.co.id",
        "sitemaps": ["https://republika.co.id/sitemap.xml"],
    },
    "liputan6.com": {
        "name": "Liputan6",
        "domain": "liputan6.com",
        "sitemaps": ["https://www.liputan6.com/sitemap.xml"],
    },
}


# ============================================================
# RESEARCH VOCABULARY
# ============================================================

CORE_TERMS = [
    "BPKH", "Badan Pengelola Keuangan Haji", "dana haji", 
    "keuangan haji", "setoran Bipih", "BPIH", "nilai manfaat",
]

OVERSIGHT_TERMS = [
    "Audit BPK", "Temuan BPK", "BPK", "KPK", "Pansus", 
    "Investigasi", "DPR RI", "Komisi VIII", "Hak Angket",
]

GOVERNANCE_TERMS = [
    "kuota haji", "penyelenggaraan haji", "tata kelola", 
    "antrean haji", "mismanagement", "biaya haji", 
    "kenaikan Bipih", "Bipih", "BPIH",
]

TRUST_TERMS = [
    "transparansi", "akuntabilitas", "keadilan", "polemik", 
    "pro kontra", "kepercayaan publik", "public trust", 
    "reputasi", "kritik", "kepercayaan jemaah",
]

ACTOR_TERMS = [
    "Kemenag", "Kementerian Agama", "Menteri Agama", 
    "KPK", "BPK", "DPR", "Komisi VIII", "Pansus",
]

PRACTICAL_EXCLUSION_TERMS = [
    "doa haji", "doa ihram", "tips kesehatan jemaah", 
    "peta maktab", "hotel jemaah", "menu makanan jemaah", 
    "koper jemaah", "cuaca di arab saudi",
]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    filename=LOG_DIR / "collector.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

print_lock = threading.Lock()
file_lock = threading.Lock()
# Global lock to prevent Rust memory panics in DDGS
ddgs_lock = threading.Lock() 

def progress(message: str):
    with print_lock:
        print(message, flush=True)


# ============================================================
# HTTP & DDGS THREAD-LOCAL
# ============================================================

_thread_local = threading.local()

def get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        _thread_local.session = s
    return _thread_local.session

def get_ddgs_instance():
    """Menggunakan thread-local untuk mencegah crash memori Rust pada curl_cffi."""
    if not hasattr(_thread_local, "ddgs"):
        _thread_local.ddgs = DDGS()
    return _thread_local.ddgs

def fetch(url: str, timeout: int = HTTP_TIMEOUT):
    try:
        return get_session().get(
            url,
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        logging.warning("FETCH_FAIL | %s | %s", url, exc)
        return None


# ============================================================
# DATA MODEL
# ============================================================

@dataclass
class Article:
    article_id: str
    title: str
    author: str
    source_name: str
    source_domain: str
    publish_date: str
    url: str
    canonical_url: str
    retrieved_at: str
    query: str
    discovery_method: str
    raw_content: str
    clean_content: str
    word_count: int
    language: str
    relevance_score: float
    relevance_label: str
    risk_category: str
    content_hash: str
    status_code: int
    date_source: str


# ============================================================
# TEXT / URL UTILS
# ============================================================

def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def sha256_text(text: str) -> str:
    return hashlib.sha256(
        normalize_text(text).lower().encode("utf-8")
    ).hexdigest()

def normalize_url(url: str) -> str:
    if not url:
        return ""
    url, _ = urldefrag(url.strip())
    p = urlparse(url)
    if p.scheme not in {"http", "https"}:
        return ""
    host = p.netloc.lower().replace("www.", "")
    path = re.sub(r"/+", "/", p.path).rstrip("/")
    ignored = {
        "utm_source", "utm_medium", "utm_campaign",
        "utm_term", "utm_content", "gclid", "fbclid",
        "ref", "output", "amp",
    }
    keep = []
    for part in p.query.split("&"):
        if not part: continue
        key = part.split("=", 1)[0].lower()
        if key not in ignored:
            keep.append(part)
    query = "&".join(keep)
    return (f"https://{host}{path}" + (f"?{query}" if query else ""))

def host_allowed(url: str, domain: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host == domain or host.endswith("." + domain)


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_meta(soup: BeautifulSoup, names: list[str]) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return normalize_text(tag["content"])

        tag = soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return normalize_text(tag["content"])
    return ""

def parse_date_value(value: str) -> datetime | None:
    if not value: return None
    try:
        dt = dateparser.parse(value, fuzzy=True)
        if not dt: return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def in_period(dt: datetime | None) -> bool:
    return bool(dt and START_DATE <= dt <= END_DATE)

def detect_publish_date(soup: BeautifulSoup) -> tuple[datetime | None, str]:
    candidates = []
    
    # Metadata.
    for prop in [
        "article:published_time", "datePublished", "publishdate",
        "pubdate", "date", "date.created", "dateCreated",
    ]:
        val = extract_meta(soup, [prop])
        if val: candidates.append((val, f"meta:{prop}"))

    # JSON-LD.
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw: continue
        try:
            data = json.loads(raw)
            stack = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            for item in stack:
                if isinstance(item, dict):
                    for key in ("datePublished", "dateCreated"):
                        if item.get(key):
                            candidates.append((str(item[key]), f"jsonld:{key}"))
        except Exception:
            pass

    # <time datetime=...>
    for tag in soup.find_all("time"):
        val = tag.get("datetime") or tag.get_text(" ", strip=True)
        if val: candidates.append((val, "time"))

    # Return first valid structured date.
    for value, source in candidates:
        dt = parse_date_value(value)
        if dt: return dt, source

    return None, ""

def extract_author(soup: BeautifulSoup) -> str:
    for key in ["author", "article:author", "parsely-author", "byl", "creator", "dc.creator"]:
        val = extract_meta(soup, [key])
        if val: return val

    for selector in ['[rel="author"]', ".author", ".writer", ".byline", '[class*="author"]', '[class*="writer"]']:
        tag = soup.select_one(selector)
        if tag:
            txt = normalize_text(tag.get_text(" ", strip=True))
            if 1 < len(txt) < 200:
                return txt
    return ""

def extract_title(soup: BeautifulSoup) -> str:
    for prop in ["og:title", "twitter:title"]:
        val = extract_meta(soup, [prop])
        if val: return val

    h1 = soup.find("h1")
    if h1:
        txt = normalize_text(h1.get_text(" ", strip=True))
        if txt: return txt

    if soup.title:
        return normalize_text(soup.title.get_text(" ", strip=True))

    return ""


# ============================================================
# ARTICLE EXTRACTION
# ============================================================

def extract_content(html: str) -> str:
    if trafilatura:
        try:
            text = trafilatura.extract(
                html, include_comments=False, include_tables=False, favor_precision=True
            )
            if text and len(text.split()) >= MIN_WORDS:
                return normalize_text(text)
        except Exception:
            pass

    # PENGUBAHAN PENTING: Gunakan 'html.parser' murni alih-alih 'lxml' 
    # untuk mencegah crash memori/C-Level ketika multi-threading 
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "aside", "iframe"]):
        tag.decompose()

    candidates = []
    for selector in ["article", "main", '[role="main"]']:
        for node in soup.select(selector):
            txt = normalize_text(node.get_text(" ", strip=True))
            if len(txt.split()) >= MIN_WORDS:
                candidates.append(txt)

    if candidates:
        return max(candidates, key=lambda x: len(x.split()))

    paragraphs = []
    for p in soup.find_all("p"):
        txt = normalize_text(p.get_text(" ", strip=True))
        if len(txt.split()) >= 5:
            paragraphs.append(txt)

    return normalize_text(" ".join(paragraphs))


# ============================================================
# QUERY DESIGN
# ============================================================

def build_queries(domain: str) -> list[str]:
    queries = []
    direct = ['"BPKH"', '"Badan Pengelola Keuangan Haji"', '"dana haji" BPKH', '"keuangan haji" BPKH', '"nilai manfaat" BPKH', '"BPIH" BPKH', '"Bipih" BPKH']
    oversight = ['"BPKH" "BPK"', '"BPKH" "KPK"', '"BPKH" "Pansus"', '"BPKH" "Komisi VIII"', '"BPKH" "DPR"', '"BPKH" audit', '"dana haji" audit', '"dana haji" KPK', '"dana haji" BPK']
    governance = ['"BPKH" "kuota haji"', '"BPKH" "tata kelola"', '"BPKH" "penyelenggaraan haji"', '"BPKH" "biaya haji"', '"BPKH" "Bipih"', '"BPKH" "BPIH"', '"dana haji" "kuota haji"', '"keuangan haji" "kuota haji"']
    trust = ['"BPKH" transparansi', '"BPKH" akuntabilitas', '"BPKH" "kepercayaan publik"', '"BPKH" reputasi', '"BPKH" kritik', '"dana haji" transparansi', '"dana haji" akuntabilitas']
    external_governance = ['"Kemenag" "kuota haji"', '"Kementerian Agama" "kuota haji"', '"Menteri Agama" "kuota haji"', '"KPK" "kuota haji"', '"BPK" "kuota haji"', '"Pansus" haji', '"Komisi VIII" haji', '"DPR" "kuota haji"']
    temporal = ['"BPKH" 2024', '"BPKH" 2025', '"BPKH" 2026', '"dana haji" 2024', '"dana haji" 2025', '"dana haji" 2026', '"kuota haji" 2024', '"kuota haji" 2025', '"kuota haji" 2026']

    all_terms = direct + oversight + governance + trust + external_governance + temporal
    for q in all_terms:
        queries.append(f"site:{domain} {q}")
    return list(dict.fromkeys(queries))


# ============================================================
# SEARCH DISCOVERY
# ============================================================

def search_engine_discovery(query: str) -> list[str]:
    if DDGS is None:
        return []
    
    urls = []
    try:
        # Gunakan lock atau instance terpisah agar memori Rust curl_cffi tidak panic
        with ddgs_lock: 
            ddgs = get_ddgs_instance()
            results = list(ddgs.text(
                query,
                max_results=MAX_SEARCH_RESULTS_PER_QUERY,
                safesearch="off",
            ))

        for item in results:
            href = normalize_url(item.get("href", ""))
            if href: urls.append(href)
            
    except Exception as exc:
        logging.warning("SEARCH_FAIL | %s | %s", query, exc)

    time.sleep(SEARCH_DELAY)
    return list(dict.fromkeys(urls))


# ============================================================
# OPTIONAL SITEMAP DISCOVERY
# ============================================================

def sitemap_discovery(domain: str, sitemap_urls: list[str]) -> list[str]:
    found = []
    visited = set()

    for sm_url in sitemap_urls:
        if sm_url in visited: continue
        visited.add(sm_url)

        r = fetch(sm_url, timeout=SEARCH_TIMEOUT)
        if not r or r.status_code != 200: continue

        soup = BeautifulSoup(r.text, "xml")
        for loc in soup.find_all("loc"):
            u = normalize_url(loc.get_text(strip=True))
            if not u: continue
            if u.endswith(".xml") or "sitemap" in u.lower(): continue

            if host_allowed(u, domain):
                low = u.lower()
                if any(term in low for term in ["bpkh", "haji", "bipih", "bpih", "dana", "keuangan", "kuota", "kemenag", "kpk", "bpk", "pansus", "investasi"]):
                    found.append(u)

    return list(dict.fromkeys(found))


# ============================================================
# RELEVANCE & NEAR DUPLICATES
# ============================================================

def term_hits(text: str, terms: list[str]) -> int:
    low = text.lower()
    return sum(1 for term in terms if term.lower() in low)

def relevance_score(title: str, content: str) -> tuple[float, str, str]:
    title_low = title.lower()
    body_low = content.lower()
    intro = body_low[:3000]

    core_title = term_hits(title_low, CORE_TERMS)
    core_intro = term_hits(intro, CORE_TERMS)
    oversight = term_hits(body_low, OVERSIGHT_TERMS)
    governance = term_hits(body_low, GOVERNANCE_TERMS)
    trust = term_hits(body_low, TRUST_TERMS)
    actors = term_hits(body_low, ACTOR_TERMS)
    exclusion = term_hits(body_low, PRACTICAL_EXCLUSION_TERMS)

    score = (
        0.32 * min(core_title / 2, 1.0)
        + 0.25 * min(core_intro / 2, 1.0)
        + 0.15 * min(governance / 3, 1.0)
        + 0.12 * min(oversight / 2, 1.0)
        + 0.10 * min(trust / 2, 1.0)
        + 0.06 * min(actors / 2, 1.0)
    )

    if exclusion >= 2 and core_title == 0 and core_intro == 0:
        score *= 0.20

    if core_title >= 1 and (governance + oversight + trust) >= 1:
        label = "TIER_1_DIRECT_BPKH"
    elif (governance + oversight) >= 2 and (core_intro >= 1 or core_title >= 1):
        label = "TIER_2_GOVERNANCE_CONTAGION"
    elif trust >= 2 and (core_intro >= 1 or core_title >= 1):
        label = "TIER_3_PUBLIC_TRUST"
    else:
        label = "EXCLUDE"

    final_label = label if label != "EXCLUDE" and score >= 0.25 else "EXCLUDE"

    risk_parts = []
    if governance: risk_parts.append("Governance")
    if oversight: risk_parts.append("Oversight")
    if core_intro or core_title: risk_parts.append("Financial")
    if trust: risk_parts.append("Public Trust")
    if any(x in body_low for x in ["likuiditas", "operasional", "penyelenggaraan"]): risk_parts.append("Operational")
    if any(x in body_low for x in ["sar", "usd", "kurs", "valas", "hedging"]): risk_parts.append("Currency")

    risk_category = ";".join(dict.fromkeys(risk_parts)) or "Unclassified"
    return round(score, 4), final_label, risk_category

def shingles(text: str, n: int = 5) -> set[str]:
    tokens = re.findall(r"\b\w+\b", text.lower())
    if len(tokens) < n: return set(tokens)
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}

class DuplicateIndex:
    def __init__(self):
        self.hashes = set()
        self.lock = threading.Lock()
        
        if HAS_DATASKETCH:
            self.lsh = MinHashLSH(threshold=0.85, num_perm=64)
            self.minhashes = {}
        else:
            self.lsh = None
            self.minhashes = {}
        self.simhashes = {}

    @staticmethod
    def make_minhash(text: str):
        m = MinHash(num_perm=64)
        for sh in shingles(text): m.update(sh.encode("utf-8"))
        return m

    @staticmethod
    def make_simhash(text: str) -> int:
        tokens = list(shingles(text, 4))
        if not tokens: return 0
        vector = [0] * 64
        for token in tokens:
            h = int(hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest(), 16)
            for i in range(64):
                if h & (1 << i): vector[i] += 1
                else: vector[i] -= 1
        value = 0
        for i, v in enumerate(vector):
            if v >= 0: value |= (1 << i)
        return value

    @staticmethod
    def hamming(a: int, b: int) -> int:
        return (a ^ b).bit_count()

    def add_existing(self, article_id: str, text: str, content_hash: str):
        self.hashes.add(content_hash)
        if HAS_DATASKETCH:
            m = self.make_minhash(text)
            self.minhashes[article_id] = m
            try: self.lsh.insert(article_id, m)
            except ValueError: pass
        else:
            self.simhashes[article_id] = self.make_simhash(text)

    def check(self, article_id: str, text: str, content_hash: str) -> tuple[bool, str]:
        if content_hash in self.hashes: return True, "exact_hash"
        
        if HAS_DATASKETCH:
            m = self.make_minhash(text)
            candidates = self.lsh.query(m)
            if candidates: return True, f"near_duplicate_of_{candidates[0]}"
        else:
            s = self.make_simhash(text)
            for other_id, other_s in self.simhashes.items():
                if self.hamming(s, other_s) <= 5: return True, f"near_duplicate_of_{other_id}"
        return False, ""


# ============================================================
# PERSISTENCE
# ============================================================

def append_csv(path: Path, row: dict):
    with file_lock:
        exists = path.exists()
        with path.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not exists: writer.writeheader()
            writer.writerow(row)

def save_article(article: Article):
    row = asdict(article)
    append_csv(MASTER_CSV, row)
    with file_lock:
        with MASTER_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def save_rejection(url, source, reason, query="", status_code=""):
    append_csv(REJECTED_CSV, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": url, "source": source, "reason": reason, "query": query, "status_code": status_code,
    })


# ============================================================
# LOAD EXISTING DATA
# ============================================================

def load_existing():
    seen_urls = set()
    duplicate_index = DuplicateIndex()
    if not MASTER_CSV.exists(): return seen_urls, duplicate_index

    progress("[RESUME] Loading existing corpus...")
    try:
        with MASTER_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                url = normalize_url(row.get("canonical_url") or row.get("url") or "")
                if url: seen_urls.add(url)
                content_hash = row.get("content_hash")
                article_id = row.get("article_id")
                content = row.get("clean_content")
                if content_hash and article_id and content:
                    duplicate_index.add_existing(article_id, content, content_hash)
    except Exception as exc:
        progress(f"[WARNING] Could not fully load existing corpus: {exc}")

    progress(f"[RESUME] Existing URLs: {len(seen_urls):,}")
    return seen_urls, duplicate_index


# ============================================================
# ARTICLE PROCESSING
# ============================================================

def process_url(url: str, source: dict, query: str, discovery_method: str):
    domain = source["domain"]
    url = normalize_url(url)
    
    if not url or not host_allowed(url, domain):
        return None, (url, source["name"], "invalid_domain", query, "")

    r = fetch(url)
    if not r:
        return None, (url, source["name"], "fetch_failed", query, "")

    time.sleep(ARTICLE_DELAY)

    if r.status_code != 200:
        return None, (url, source["name"], "non_200", query, r.status_code)

    final_url = normalize_url(r.url)
    if not host_allowed(final_url, domain):
        return None, (url, source["name"], "redirected_outside_source", query, r.status_code)

    content_type = r.headers.get("content-type", "").lower()
    if "html" not in content_type:
        return None, (final_url, source["name"], "not_html", query, r.status_code)

    html = r.text
    
    # Memastikan memori dibersihkan dari Parser sebelumnya
    soup = BeautifulSoup(html, "html.parser")
    title = extract_title(soup)
    
    if not title:
        soup.decompose()
        return None, (final_url, source["name"], "missing_title", query, r.status_code)

    pub_dt, date_source = detect_publish_date(soup)
    if not pub_dt:
        soup.decompose()
        return None, (final_url, source["name"], "missing_publish_date", query, r.status_code)

    if not in_period(pub_dt):
        soup.decompose()
        return None, (final_url, source["name"], "out_of_period", query, r.status_code)

    content = extract_content(html)
    soup.decompose() # Cleanup explicit
    
    if not content or len(content.split()) < MIN_WORDS:
        return None, (final_url, source["name"], "insufficient_full_text", query, r.status_code)

    try: language = detect(content[:5000])
    except LangDetectException: language = "unknown"

    if language != "id":
        return None, (final_url, source["name"], f"language_{language}", query, r.status_code)

    score, relevance_label, risk_category = relevance_score(title, content)
    if relevance_label == "EXCLUDE":
        return None, (final_url, source["name"], "relevance_gate", query, r.status_code)

    content_hash = sha256_text(content)
    article_id = hashlib.sha256((source["domain"] + "|" + final_url + "|" + content_hash).encode("utf-8")).hexdigest()[:32]

    article = Article(
        article_id=article_id, title=title, author=extract_author(BeautifulSoup(html, "html.parser")),
        source_name=source["name"], source_domain=domain, publish_date=pub_dt.isoformat(),
        url=url, canonical_url=final_url, retrieved_at=datetime.now(timezone.utc).isoformat(),
        query=query, discovery_method=discovery_method, raw_content=content,
        clean_content=content, word_count=len(content.split()), language=language,
        relevance_score=score, relevance_label=relevance_label, risk_category=risk_category,
        content_hash=content_hash, status_code=r.status_code, date_source=date_source,
    )
    return article, None


# ============================================================
# SOURCE COLLECTION
# ============================================================

def collect_source(domain: str, source: dict, seen_urls: set[str], duplicate_index: DuplicateIndex):
    progress(f"\n{'=' * 72}\n[SOURCE] {source['name']} | {domain}\n{'=' * 72}")
    queries = build_queries(domain)
    progress(f"[{source['name']}] Search queries: {len(queries)}")

    candidates = {}
    completed_queries = 0

    def search_one(query):
        return query, search_engine_discovery(query)

    if DDGS is None:
        progress("[ERROR] DDGS not installed. Run: pip install ddgs")
    else:
        with ThreadPoolExecutor(max_workers=SEARCH_WORKERS) as executor:
            futures = [executor.submit(search_one, q) for q in queries]
            for future in as_completed(futures):
                query, urls = future.result()
                completed_queries += 1
                for url in urls:
                    if host_allowed(url, domain):
                        candidates.setdefault(url, query)
                progress(f"[{source['name']}] Search {completed_queries}/{len(queries)} | unique URLs={len(candidates):,}")
    
    gc.collect() # Trigger Garbage Collection

    if USE_SITEMAPS:
        progress(f"[{source['name']}] Sitemap discovery...")
        sitemap_urls = sitemap_discovery(domain, source["sitemaps"])
        for url in sitemap_urls: candidates.setdefault(url, "sitemap")
        progress(f"[{source['name']}] Sitemap candidates added: {len(sitemap_urls):,}")

    candidate_items = [(url, query) for url, query in candidates.items() if url not in seen_urls]
    if MAX_CANDIDATES_PER_SOURCE:
        candidate_items = candidate_items[:MAX_CANDIDATES_PER_SOURCE]

    progress(f"[{source['name']}] Candidates to fetch: {len(candidate_items):,}")
    if not candidate_items: return 0

    accepted_count = 0
    processed = 0
    total = len(candidate_items)

    def worker(item):
        url, query = item
        discovery_method = "sitemap" if query == "sitemap" else "search_engine"
        return process_url(url, source, query, discovery_method)

    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS) as executor:
        futures = [executor.submit(worker, item) for item in candidate_items]
        for future in as_completed(futures):
            article, rejection = future.result()
            processed += 1

            if article:
                is_dup, dup_reason = duplicate_index.check(article.article_id, article.clean_content, article.content_hash)
                if is_dup:
                    save_rejection(article.canonical_url, article.source_name, dup_reason, article.query, article.status_code)
                else:
                    raw_path = RAW_DIR / f"{article.article_id}.txt"
                    raw_path.write_text(article.raw_content, encoding="utf-8")
                    save_article(article)
                    duplicate_index.add_existing(article.article_id, article.clean_content, article.content_hash)
                    seen_urls.add(article.canonical_url)
                    accepted_count += 1
                    progress(f"[{source['name']}] ACCEPT {accepted_count:,} | {processed:,}/{total:,} | {article.publish_date[:10]} | {article.relevance_label} | {article.title[:90]}")
            
            elif rejection:
                save_rejection(*rejection)

            if processed % 25 == 0 and processed > 0:
                progress(f"[{source['name']}] PROGRESS {processed:,}/{total:,} | accepted={accepted_count:,}")
                gc.collect() # Bersihkan memori per 25 artikel

    progress(f"[{source['name']}] DONE | processed={processed:,} | accepted={accepted_count:,}")
    return accepted_count


# ============================================================
# MAIN
# ============================================================

def main():
    start_clock = time.time()
    progress("\n" + "=" * 72)
    progress("BPKH NEWS CORPUS COLLECTOR v2 (Memory-Safe Version)")
    progress("=" * 72)
    progress(f"Period : {START_DATE.date()} -> {END_DATE.date()}")
    progress(f"Sources: {len(SOURCES)}")
    progress(f"Workers: search={SEARCH_WORKERS}, article={ARTICLE_WORKERS}")
    progress(f"Sitemaps: {'ON' if USE_SITEMAPS else 'OFF'}")

    if DDGS is None:
        progress("\n[STOP] Search engine package not found.")
        progress("Install with: pip install ddgs")
        return

    seen_urls, duplicate_index = load_existing()
    total_accepted = 0

    for domain, source in SOURCES.items():
        accepted = collect_source(domain, source, seen_urls, duplicate_index)
        total_accepted += accepted
        gc.collect() # Bersihkan RAM penuh setelah 1 domain selesai

    elapsed = time.time() - start_clock
    progress("\n" + "=" * 72)
    progress("COLLECTION FINISHED")
    progress("=" * 72)
    progress(f"Accepted this run : {total_accepted:,}")
    progress(f"Total elapsed      : {elapsed / 60:.1f} minutes")
    progress(f"Master CSV         : {MASTER_CSV}")
    progress(f"Master JSONL       : {MASTER_JSONL}")
    progress(f"Rejected           : {REJECTED_CSV}")
    progress(f"Log                : {LOG_DIR / 'collector.log'}")
    progress("\nIMPORTANT: Search snippets were NOT used as article content.")
    progress("Publication dates were taken from article-page metadata/time tags.")


if __name__ == "__main__":
    main()
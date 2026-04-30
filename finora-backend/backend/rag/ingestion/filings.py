"""
Ingest SEC EDGAR 10-K / 10-Q filings → SemanticChunker → Qdrant (finora_filings).
No API key needed. User-Agent set per SEC fair use policy.
"""
from __future__ import annotations

import os
import re
import time
import uuid

import requests
import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from backend.rag.chunking.strategies import SemanticChunker
from backend.rag.embedder import embed_batch
from backend.rag.ingestion.collections import collection_name, get_client

log = structlog.get_logger()

_chunker = SemanticChunker(threshold=0.75, min_tokens=300, max_tokens=800)

_EDGAR_BASE = "https://data.sec.gov"
_HEADERS = {"User-Agent": os.getenv("SEC_EDGAR_USER_AGENT", "contact@finora.app")}
_FORM_TYPES = {"10-K", "10-Q"}
_SEC_MAP = None

def _load_sec_map():
    global _SEC_MAP
    if _SEC_MAP:
        return _SEC_MAP

    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        _SEC_MAP = {
            entry["ticker"].upper(): str(entry["cik_str"]).zfill(10)
            for entry in data.values()
        }
        return _SEC_MAP

    except Exception as exc:
        log.error("sec_map_failed", error=str(exc))
        return {}


def _get_cik(ticker: str) -> str | None:
    sec_map = _load_sec_map()
    return sec_map.get(ticker.upper())


def _get_recent_filings(cik: str, max_filings: int = 3) -> list[dict]:
    try:
        resp = requests.get(
            f"{_EDGAR_BASE}/submissions/CIK{cik}.json",
            headers=_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        primary_docs = recent.get("primaryDocument", [])

        filings = []
        for form, acc, dt, doc in zip(forms, accessions, dates, primary_docs):
            if form in _FORM_TYPES and len(filings) < max_filings:
                filings.append({
                    "form": form,
                    "accession": acc.replace("-", ""),
                    "date": dt,
                    "primary_doc": doc,
                    "cik": cik,
                })
        return filings
    except Exception as exc:
        log.error("edgar_filings_fetch_failed", cik=cik, error=str(exc))
        return []


def _fetch_filing_text(cik: str, accession: str, primary_doc: str) -> str:
    url = f"https://www.sec.gov/Archives/edgar/full-index/{cik[:4]}/{cik[4:]}"
    # Direct document URL
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
    try:
        resp = requests.get(filing_url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()

        # Strip HTML tags if present
        text = resp.text
        if "<html" in text.lower() or "<HTML" in text:
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"&[a-z]+;", " ", text)
            text = re.sub(r"\s{3,}", "\n\n", text)

        words = text.split()
        if len(words) > 8000:
            text = " ".join(words[:8000])

        return text.strip()
    except Exception as exc:
        log.error("edgar_filing_download_failed", url=filing_url, error=str(exc))
        return ""


def ingest_ticker(
    ticker: str,
    client: QdrantClient | None = None,
    max_filings: int = 2,
) -> int:
    
    log.info("filing_start", ticker=ticker)

    # Only US tickers — NIFTY 50 uses Indian exchanges, no SEC filings
    if ticker.endswith((".NS", ".BO")):
        return 0

    c = client or get_client()
    col = collection_name("filings")

    cik = _get_cik(ticker)
    if not cik:
        log.warning("edgar_no_cik", ticker=ticker)
        return 0

    filings = _get_recent_filings(cik, max_filings)

    log.info("filings_found", ticker=ticker, count=len(filings))

    if not filings:
        return 0

    total_chunks = 0
    for filing in filings:
        time.sleep(1)
        text = _fetch_filing_text(filing["cik"], filing["accession"], filing["primary_doc"])
        if len(text) < 500:
            continue

        meta = {
            "ticker": ticker,
            "filing_type": filing["form"],
            "period": filing["date"],
            "cik": filing["cik"],
            "accession": filing["accession"],
            "source": "sec_edgar",
        }
        chunks = _chunker.chunk(text, metadata=meta)
        if not chunks:
            continue

        texts = [ch.text for ch in chunks]
        vectors = embed_batch(texts)

        points = [
            PointStruct(
                id=str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{ticker}:{filing['accession']}:{i}",
                )),
                vector=vec,
                payload={**ch.metadata, "text": ch.text, "data_type": "filing"},
            )
            for i, (ch, vec) in enumerate(zip(chunks, vectors))
        ]

        c.upsert(collection_name=col, points=points)
        total_chunks += len(points)
        log.info("filing_ingest_done", ticker=ticker, form=filing["form"], chunks=len(points))

    return total_chunks

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

from rag.chunking.strategies import SemanticChunker
from rag.embedder import embed_batch
from rag.ingestion.collections import collection_name, get_client

log = structlog.get_logger()

_chunker = SemanticChunker(threshold=0.75, min_tokens=300, max_tokens=800)

_EDGAR_BASE = "https://data.sec.gov"
_HEADERS = {"User-Agent": os.getenv("SEC_EDGAR_USER_AGENT", "contact@finora.app")}
_FORM_TYPES = {"10-K", "10-Q"}


def _get_cik(ticker: str) -> str | None:
    """Look up SEC CIK number for a ticker."""
    try:
        resp = requests.get(
            f"{_EDGAR_BASE}/submissions/",
            params={"action": "getcompany", "company": ticker, "type": "10-K", "dateb": "", "owner": "include"},
            headers=_HEADERS,
            timeout=10,
        )
        # Use the company tickers JSON instead — faster and reliable
        tickers_resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=_HEADERS,
            timeout=10,
        )
        tickers_resp.raise_for_status()
        data = tickers_resp.json()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"]).zfill(10)
    except Exception as exc:
        log.error("edgar_cik_lookup_failed", ticker=ticker, error=str(exc))
    return None


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

        # Take middle section (skip boilerplate headers/footers)
        words = text.split()
        if len(words) > 2000:
            text = " ".join(words[200:8000])  # ~7800 words of substantive content

        return text.strip()
    except Exception as exc:
        log.error("edgar_filing_download_failed", url=filing_url, error=str(exc))
        return ""


def ingest_ticker(
    ticker: str,
    client: QdrantClient | None = None,
    max_filings: int = 2,
) -> int:
    # Only US tickers — NIFTY 50 uses Indian exchanges, no SEC filings
    if ticker.endswith(".NS") or ticker.endswith(".BSE"):
        return 0

    c = client or get_client()
    col = collection_name("filings")

    cik = _get_cik(ticker)
    if not cik:
        log.warning("edgar_no_cik", ticker=ticker)
        return 0

    filings = _get_recent_filings(cik, max_filings)
    if not filings:
        return 0

    total_chunks = 0
    for filing in filings:
        time.sleep(0.5)  # SEC fair use: no hammering
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

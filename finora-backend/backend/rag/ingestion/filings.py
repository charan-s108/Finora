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


# Sections worth extracting per form type — everything else is boilerplate
_TARGET_SECTIONS: dict[str, list[tuple[str, str]]] = {
    "10-K": [
        ("business",      r"item\s+1[\.\s]+business\b"),
        ("risk_factors",  r"item\s+1a[\.\s]+risk\s+factor"),
        ("mda",           r"item\s+7[\.\s]+management.{0,60}discussion"),
        ("market_risk",   r"item\s+7a[\.\s]+quantitative"),
    ],
    "10-Q": [
        ("mda",           r"item\s+2[\.\s]+management.{0,60}discussion"),
        ("market_risk",   r"item\s+3[\.\s]+quantitative"),
    ],
}

# Human-readable labels for section metadata
_SECTION_LABELS = {
    "business":     "Business Description",
    "risk_factors": "Risk Factors",
    "mda":          "Management Discussion & Analysis",
    "market_risk":  "Market Risk",
}

_NEXT_ITEM = re.compile(r"\bitem\s+\d+[a-z]?[\.\s]", re.IGNORECASE)


def _clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&[a-z]{2,6};", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def _extract_sections(raw: str, form_type: str) -> list[dict]:
    """
    Parse filing text and return only high-value sections tagged by name.
    Falls back to full text (truncated) if no sections matched.
    """
    text = _clean_html(raw) if ("<html" in raw.lower()) else raw
    text_lower = text.lower()

    patterns = _TARGET_SECTIONS.get(form_type, _TARGET_SECTIONS["10-K"])
    found: list[tuple[int, str, str]] = []  # (start_pos, section_key, label)

    for key, pattern in patterns:
        for m in re.finditer(pattern, text_lower):
            found.append((m.end(), key, _SECTION_LABELS[key]))
            break  # first match only — skip table-of-contents repeats by taking the last match

    # Re-run taking the LAST occurrence of each key (skips TOC, hits actual section)
    found_last: dict[str, tuple[int, str]] = {}
    for key, pattern in patterns:
        matches = list(re.finditer(pattern, text_lower))
        if matches:
            m = matches[-1]
            found_last[key] = (m.end(), _SECTION_LABELS[key])

    if not found_last:
        # No sections detected — fall back to first 6000 words
        words = text.split()
        return [{"section": "full_text", "label": "Filing Text", "text": " ".join(words[:6000])}]

    # Sort by position, extract text up to the next known section start
    ordered = sorted(found_last.items(), key=lambda x: x[1][0])
    result = []
    for i, (key, (start, label)) in enumerate(ordered):
        end = ordered[i + 1][1][0] if i + 1 < len(ordered) else len(text)
        section_text = text[start:end].strip()
        # Cap each section at 4000 words to avoid embedding huge chunks
        words = section_text.split()
        if len(words) > 4000:
            section_text = " ".join(words[:4000])
        if len(section_text) > 300:
            result.append({"section": key, "label": label, "text": section_text})

    return result if result else [{"section": "full_text", "label": "Filing Text",
                                   "text": " ".join(text.split()[:6000])}]


def _fetch_raw_filing(cik: str, accession: str, primary_doc: str) -> str:
    filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
    try:
        resp = requests.get(filing_url, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
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
        raw = _fetch_raw_filing(filing["cik"], filing["accession"], filing["primary_doc"])
        if len(raw) < 500:
            continue

        sections = _extract_sections(raw, filing["form"])
        filing_points: list[PointStruct] = []

        for sec in sections:
            base_meta = {
                "ticker": ticker,
                "filing_type": filing["form"],
                "period": filing["date"],
                "cik": filing["cik"],
                "accession": filing["accession"],
                "section": sec["section"],
                "section_label": sec["label"],
                "source": "sec_edgar",
            }
            chunks = _chunker.chunk(sec["text"], metadata=base_meta)
            if not chunks:
                continue

            texts = [ch.text for ch in chunks]
            vectors = embed_batch(texts)

            for i, (ch, vec) in enumerate(zip(chunks, vectors)):
                filing_points.append(PointStruct(
                    id=str(uuid.uuid5(
                        uuid.NAMESPACE_DNS,
                        f"{ticker}:{filing['accession']}:{sec['section']}:{i}",
                    )),
                    vector=vec,
                    payload={**ch.metadata, "text": ch.text, "data_type": "filing"},
                ))

        if filing_points:
            c.upsert(collection_name=col, points=filing_points)
            total_chunks += len(filing_points)
            log.info("filing_ingest_done", ticker=ticker, form=filing["form"],
                     sections=len(sections), chunks=len(filing_points))

    return total_chunks

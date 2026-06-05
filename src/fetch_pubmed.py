"""Collect PubMed metadata for retinal-dystrophy research queries.

Stage 1 of the pipeline. Uses NCBI Entrez (via Biopython) to:
  1. esearch  -> get the list of PMIDs matching each query
  2. efetch   -> pull full records in batches and parse the fields we need
and writes the merged, de-duplicated result to data/raw/pubmed_records.json.

Usage:
    python src/fetch_pubmed.py                 # all queries, default caps
    python src/fetch_pubmed.py --max 200       # cap each query at 200 records
    python src/fetch_pubmed.py --query cone_dystrophy

Set NCBI_EMAIL (required) and NCBI_API_KEY (optional) in a .env file first;
see .env.example.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Iterable

from Bio import Entrez

import config

# NCBI batch size for efetch. 200 keeps each request small and well within limits.
BATCH_SIZE = 200
# Polite pause between requests when no API key is set (limit is 3 req/s).
SLEEP_NO_KEY = 0.34
SLEEP_WITH_KEY = 0.11


def _configure_entrez() -> bool:
    """Wire up Entrez credentials. Returns True if an API key is in use."""
    email, api_key = config.get_entrez_credentials()
    if not email:
        sys.exit(
            "ERROR: NCBI_EMAIL is not set. Copy .env.example to .env and add "
            "your email (NCBI requires it for Entrez requests)."
        )
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key
    return bool(api_key)


def _build_query(base_query: str) -> str:
    """Append the publication-year filter from config to a base query."""
    lo, hi = config.YEAR_MIN, config.YEAR_MAX
    if lo is None and hi is None:
        return base_query
    lo_s = str(lo) if lo is not None else "1800"
    hi_s = str(hi) if hi is not None else "3000"
    return f"({base_query}) AND ({lo_s}:{hi_s}[Date - Publication])"


def search_pmids(query: str, max_results: int) -> list[str]:
    """Return up to `max_results` PMIDs matching `query`."""
    handle = Entrez.esearch(
        db="pubmed", term=query, retmax=max_results, sort="pub_date"
    )
    record = Entrez.read(handle)
    handle.close()
    return list(record.get("IdList", []))


def _first_text(parent: dict, key: str, default: str = "") -> str:
    """Safely pull a string field that Entrez may return as str or list."""
    value = parent.get(key, default)
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value)


def _parse_year(article: dict) -> int | None:
    """Extract a 4-digit publication year, trying several Entrez locations."""
    journal = article.get("Journal", {})
    pubdate = journal.get("JournalIssue", {}).get("PubDate", {})
    year = pubdate.get("Year")
    if year and str(year)[:4].isdigit():
        return int(str(year)[:4])
    # Fallback: MedlineDate is a free-text field like "2019 Jun-Jul".
    medline = pubdate.get("MedlineDate", "")
    for token in str(medline).split():
        if token[:4].isdigit() and len(token) >= 4:
            return int(token[:4])
    return None


def _parse_authors(article: dict) -> list[str]:
    """Return author names as 'LastName Initials' strings."""
    authors = []
    for a in article.get("AuthorList", []):
        last = a.get("LastName")
        initials = a.get("Initials", "")
        if last:
            authors.append(f"{last} {initials}".strip())
        elif a.get("CollectiveName"):
            authors.append(str(a["CollectiveName"]))
    return authors


def _parse_affiliations(article: dict) -> list[str]:
    """Return the unique affiliation strings listed across all authors.

    PubMed records carry affiliations per author (often only for some), as free
    text. We collect the distinct strings; institution normalisation happens in
    the analysis stage.
    """
    seen: list[str] = []
    for a in article.get("AuthorList", []):
        for info in a.get("AffiliationInfo", []):
            aff = str(info.get("Affiliation", "")).strip()
            if aff and aff not in seen:
                seen.append(aff)
    return seen


def _parse_abstract(article: dict) -> str:
    """Join the (possibly multi-section) abstract into one string."""
    abstract = article.get("Abstract", {}).get("AbstractText", [])
    if isinstance(abstract, str):
        return abstract
    parts = []
    for chunk in abstract:
        # Structured abstracts carry a 'Label' attribute on each chunk.
        label = getattr(chunk, "attributes", {}).get("Label")
        text = str(chunk)
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts)


def _parse_keywords(citation: dict) -> list[str]:
    """Collect MeSH headings and author keywords for one citation."""
    terms: list[str] = []
    for mesh in citation.get("MeshHeadingList", []):
        descriptor = mesh.get("DescriptorName")
        if descriptor:
            terms.append(str(descriptor))
    for kw_list in citation.get("KeywordList", []):
        terms.extend(str(kw) for kw in kw_list)
    return terms


def parse_records(raw: dict, query_label: str) -> list[dict[str, Any]]:
    """Turn one efetch response into a list of flat record dicts."""
    out = []
    for entry in raw.get("PubmedArticle", []):
        citation = entry.get("MedlineCitation", {})
        article = citation.get("Article", {})
        out.append(
            {
                "pmid": _first_text(citation, "PMID"),
                "title": _first_text(article, "ArticleTitle"),
                "year": _parse_year(article),
                "journal": _first_text(article.get("Journal", {}), "Title"),
                "authors": _parse_authors(article),
                "affiliations": _parse_affiliations(article),
                "abstract": _parse_abstract(article),
                "keywords": _parse_keywords(citation),
                "query_labels": [query_label],
            }
        )
    return out


def fetch_details(pmids: list[str], query_label: str, sleep: float) -> Iterable[dict]:
    """Fetch and parse full records for a list of PMIDs, batch by batch."""
    from tqdm import tqdm

    for start in tqdm(
        range(0, len(pmids), BATCH_SIZE),
        desc=f"  {query_label}",
        unit="batch",
        leave=False,
    ):
        batch = pmids[start : start + BATCH_SIZE]
        handle = Entrez.efetch(
            db="pubmed", id=",".join(batch), rettype="xml", retmode="xml"
        )
        raw = Entrez.read(handle)
        handle.close()
        yield from parse_records(raw, query_label)
        time.sleep(sleep)


def merge_records(all_records: list[dict]) -> list[dict]:
    """De-duplicate by PMID, unioning the query labels that surfaced each one."""
    by_pmid: dict[str, dict] = {}
    for rec in all_records:
        pmid = rec["pmid"]
        if not pmid:
            continue
        if pmid in by_pmid:
            existing = by_pmid[pmid]["query_labels"]
            for label in rec["query_labels"]:
                if label not in existing:
                    existing.append(label)
        else:
            by_pmid[pmid] = rec
    return list(by_pmid.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        choices=list(config.SEARCH_QUERIES),
        help="Run only one named query (default: all).",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=config.MAX_RESULTS_PER_QUERY,
        help="Max records per query.",
    )
    args = parser.parse_args()

    has_key = _configure_entrez()
    sleep = SLEEP_WITH_KEY if has_key else SLEEP_NO_KEY
    queries = (
        {args.query: config.SEARCH_QUERIES[args.query]}
        if args.query
        else config.SEARCH_QUERIES
    )

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_records: list[dict] = []

    for label, base_query in queries.items():
        query = _build_query(base_query)
        print(f"[{label}] searching PubMed...")
        pmids = search_pmids(query, args.max)
        print(f"[{label}] {len(pmids)} PMIDs found; fetching details...")
        all_records.extend(fetch_details(pmids, label, sleep))

    merged = merge_records(all_records)
    out_path = config.RAW_DIR / "pubmed_records.json"
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2))

    print(
        f"\nDone. {len(merged)} unique records "
        f"(from {len(all_records)} total hits) -> {out_path}"
    )


if __name__ == "__main__":
    main()

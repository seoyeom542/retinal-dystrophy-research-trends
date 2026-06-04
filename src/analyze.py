"""Analyze collected PubMed records into summary tables.

Stage 2 of the pipeline. Reads data/raw/pubmed_records.json and produces the
aggregate tables the visualization stage consumes, written to
data/processed/ as JSON:

  yearly_counts.json      year -> publication count (overall + per query)
  gene_mentions.json      gene -> number of records mentioning it
  treatment_trends.json   modality -> count, and modality x year matrix
  top_journals.json       journal -> count
  keyword_cooccurrence.json  top co-occurring keyword pairs
  summary.json            headline numbers for the dashboard

Usage:
    python src/analyze.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from itertools import combinations
from typing import Any

import pandas as pd

import config


def load_records() -> pd.DataFrame:
    """Load raw records into a DataFrame with a combined searchable text column."""
    path = config.RAW_DIR / "pubmed_records.json"
    if not path.exists():
        raise SystemExit(
            f"No data at {path}. Run `python src/fetch_pubmed.py` first."
        )
    records = json.loads(path.read_text())
    df = pd.DataFrame(records)
    # One lowercased text blob per record for case-insensitive keyword search.
    df["search_text"] = (
        df["title"].fillna("")
        + " "
        + df["abstract"].fillna("")
        + " "
        + df["keywords"].apply(lambda ks: " ".join(ks) if isinstance(ks, list) else "")
    ).str.lower()
    # Title+abstract+keywords with original case, for case-sensitive gene symbols.
    df["gene_text"] = (
        df["title"].fillna("")
        + " "
        + df["abstract"].fillna("")
        + " "
        + df["keywords"].apply(lambda ks: " ".join(ks) if isinstance(ks, list) else "")
    )
    return df


def yearly_counts(df: pd.DataFrame) -> dict[str, Any]:
    """Publication counts per year, overall and broken down by query label."""
    valid = df[df["year"].notna()].copy()
    valid["year"] = valid["year"].astype(int)

    overall = valid["year"].value_counts().sort_index()
    result: dict[str, Any] = {
        "overall": {int(y): int(c) for y, c in overall.items()},
        "by_query": {},
    }
    for label in config.SEARCH_QUERIES:
        mask = valid["query_labels"].apply(lambda labels: label in labels)
        counts = valid[mask]["year"].value_counts().sort_index()
        result["by_query"][label] = {int(y): int(c) for y, c in counts.items()}
    return result


def gene_mentions(df: pd.DataFrame) -> dict[str, int]:
    """Count records mentioning each gene (case-sensitive, whole-word match)."""
    counts: dict[str, int] = {}
    for gene in config.RETINAL_GENES:
        # \b word boundary so "RP1" doesn't match "RP100"; case-sensitive symbol.
        pattern = re.compile(rf"\b{re.escape(gene)}\b")
        counts[gene] = int(df["gene_text"].apply(lambda t: bool(pattern.search(t))).sum())
    # Sort descending, drop genes with zero hits.
    return dict(
        sorted(
            ((g, c) for g, c in counts.items() if c > 0),
            key=lambda kv: kv[1],
            reverse=True,
        )
    )


def treatment_trends(df: pd.DataFrame) -> dict[str, Any]:
    """Count records per treatment modality, plus a modality x year matrix."""
    valid = df.copy()
    valid["year"] = valid["year"]

    totals: dict[str, int] = {}
    by_year: dict[str, dict[int, int]] = {}

    for modality, keywords in config.TREATMENT_KEYWORDS.items():
        # A record counts once for a modality if it matches ANY of its keywords.
        pattern = re.compile("|".join(re.escape(k.lower()) for k in keywords))
        mask = valid["search_text"].apply(lambda t: bool(pattern.search(t)))
        matched = valid[mask]
        totals[modality] = int(mask.sum())

        years = matched[matched["year"].notna()].copy()
        years["year"] = years["year"].astype(int)
        counts = years["year"].value_counts().sort_index()
        by_year[modality] = {int(y): int(c) for y, c in counts.items()}

    return {
        "totals": dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True)),
        "by_year": by_year,
    }


def top_journals(df: pd.DataFrame, top_n: int = 15) -> dict[str, int]:
    """Most frequent journals in the dataset."""
    counts = df["journal"].fillna("").replace("", pd.NA).dropna().value_counts()
    return {str(j): int(c) for j, c in counts.head(top_n).items()}


def keyword_cooccurrence(df: pd.DataFrame, top_n: int = 30) -> list[dict[str, Any]]:
    """Top co-occurring keyword pairs across records.

    Uses MeSH/author keywords. Generic, near-universal terms are filtered so
    the result highlights topical structure rather than boilerplate.
    """
    stop_terms = {
        "humans", "human", "animals", "female", "male", "adult", "aged",
        "middle aged", "child", "adolescent", "young adult", "retrospective studies",
        "mutation", "pedigree", "phenotype", "genotype",
    }
    pair_counter: Counter[tuple[str, str]] = Counter()
    for keywords in df["keywords"]:
        if not isinstance(keywords, list):
            continue
        cleaned = sorted(
            {k.strip() for k in keywords if k.strip().lower() not in stop_terms and len(k.strip()) > 2}
        )
        for a, b in combinations(cleaned, 2):
            pair_counter[(a, b)] += 1

    return [
        {"source": a, "target": b, "weight": int(w)}
        for (a, b), w in pair_counter.most_common(top_n)
    ]


def build_summary(df: pd.DataFrame, genes: dict[str, int], treatments: dict) -> dict:
    """Headline numbers for the dashboard hero section."""
    years = df[df["year"].notna()]["year"].astype(int)
    top_gene = next(iter(genes), None)
    top_treatment = next(iter(treatments["totals"]), None)
    return {
        "total_records": int(len(df)),
        "year_range": [int(years.min()), int(years.max())] if len(years) else None,
        "records_with_abstract": int((df["abstract"].fillna("") != "").sum()),
        "unique_journals": int(df["journal"].fillna("").replace("", pd.NA).nunique()),
        "top_gene": {"name": top_gene, "count": genes.get(top_gene)} if top_gene else None,
        "top_treatment": {
            "name": top_treatment,
            "count": treatments["totals"].get(top_treatment),
        }
        if top_treatment
        else None,
    }


def _write(name: str, obj: Any) -> None:
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PROCESSED_DIR / name
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
    print(f"  wrote {path.relative_to(config.PROJECT_ROOT)}")


def main() -> None:
    df = load_records()
    print(f"Loaded {len(df)} records. Analyzing...")

    genes = gene_mentions(df)
    treatments = treatment_trends(df)

    _write("yearly_counts.json", yearly_counts(df))
    _write("gene_mentions.json", genes)
    _write("treatment_trends.json", treatments)
    _write("top_journals.json", top_journals(df))
    _write("keyword_cooccurrence.json", keyword_cooccurrence(df))
    _write("summary.json", build_summary(df, genes, treatments))

    print("\nTop 5 genes:", list(genes.items())[:5])
    print("Treatment totals:", treatments["totals"])


if __name__ == "__main__":
    main()

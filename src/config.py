"""Shared configuration: search queries, paths, and gene/treatment vocabularies.

Keeping these in one place means the collection, analysis, and visualization
stages all agree on what "the dataset" is.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# --- PubMed search queries -------------------------------------------------
# Each entry is a (label, query) pair. The label tags every record so we can
# tell which search surfaced it (records may match more than one query).
# Query syntax follows PubMed's field tags: [Title/Abstract], [MeSH Terms], etc.
SEARCH_QUERIES: dict[str, str] = {
    "cone_dystrophy": (
        '("cone dystrophy"[Title/Abstract] '
        'OR "cone-rod dystrophy"[Title/Abstract] '
        'OR "cone dystrophy"[MeSH Terms])'
    ),
    "inherited_retinal_dystrophy": (
        '("inherited retinal dystrophy"[Title/Abstract] '
        'OR "inherited retinal disease"[Title/Abstract] '
        'OR "retinal dystrophy"[MeSH Terms])'
    ),
    "retinal_gene_therapy": (
        '("retina"[Title/Abstract] OR "retinal"[Title/Abstract]) '
        'AND ("gene therapy"[Title/Abstract] OR "gene therapy"[MeSH Terms])'
    ),
}

# Restrict to a sensible publication-year window (inclusive). None = no bound.
YEAR_MIN: int | None = 2000
YEAR_MAX: int | None = 2025

# Hard cap on records pulled per query, to keep first runs fast and friendly
# to NCBI. Raise once you're confident in the pipeline.
MAX_RESULTS_PER_QUERY = 2000

# --- Domain vocabularies (used in the analysis stage) ----------------------
# Genes commonly implicated in inherited retinal dystrophies. Matched
# case-sensitively as whole words against titles/abstracts/keywords.
RETINAL_GENES: list[str] = [
    "ABCA4", "RPGR", "GUCA1A", "GUCY2D", "KCNV2", "PDE6C", "PDE6H",
    "CNGA3", "CNGB3", "RPE65", "CRX", "PROM1", "RIMS1", "PRPH2",
    "RP1", "RHO", "USH2A", "CEP290", "CRB1", "BEST1", "NR2E3",
    "CHM", "RS1", "ELOVL4", "AIPL1", "RDH12", "CDHR1",
]

# Treatment / modality keywords -> human-readable bucket.
TREATMENT_KEYWORDS: dict[str, list[str]] = {
    "Gene therapy": ["gene therapy", "gene replacement", "AAV", "adeno-associated"],
    "Gene editing": ["CRISPR", "base editing", "prime editing", "gene editing"],
    "Stem cell": ["stem cell", "iPSC", "induced pluripotent", "cell transplant"],
    "Optogenetics": ["optogenetic", "channelrhodopsin", "optogenetics"],
    "Antisense oligonucleotide": ["antisense oligonucleotide", "ASO", "splice modulation"],
    "Retinal prosthesis": ["retinal prosthesis", "retinal implant", "bionic eye"],
    "Pharmacological": ["pharmacolog", "small molecule", "drug treatment"],
}


def get_entrez_credentials() -> tuple[str, str | None]:
    """Return (email, api_key) for NCBI Entrez, loaded from the environment.

    Email is required by NCBI. API key is optional but lifts the rate limit.
    Reads a .env file if python-dotenv is installed.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass  # .env support is optional; env vars still work.

    email = os.environ.get("NCBI_EMAIL", "").strip()
    api_key = os.environ.get("NCBI_API_KEY", "").strip() or None
    return email, api_key

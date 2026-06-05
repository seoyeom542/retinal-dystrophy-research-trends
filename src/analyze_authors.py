"""Author and institution analysis of the PubMed corpus.

Companion to analyze.py. Surfaces the people and centres driving the field —
including where a given researcher ranks. Reads data/raw/pubmed_records.json and
writes data/processed/author_analysis.json with:

  top_authors        author -> paper count (ranked)
  highlight          a spotlighted author's rank/count (default: Michaelides M)
  top_institutions   normalised institution -> paper count
  top_collaborations co-authorship pairs among the most prolific authors

Usage:
    python src/analyze_authors.py
    python src/analyze_authors.py --highlight "MacLaren RE"
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import combinations

import config

# Major centres in the inherited-retinal-disease field, with the substrings that
# identify them in free-text PubMed affiliations. Counting by canonical name
# consolidates the many spelling/word-order variants of the same institution.
# Order matters only for readability; matching checks every alias.
INSTITUTION_ALIASES: dict[str, list[str]] = {
    "University College London (UCL)": ["university college london", "ucl institute", "institute of ophthalmology, ucl"],
    "Moorfields Eye Hospital": ["moorfields"],
    "University of Tübingen": ["tübingen", "tubingen"],
    "Radboud University Nijmegen": ["radboud", "nijmegen"],
    "University of California, San Francisco": ["san francisco", "ucsf"],
    "Columbia University": ["columbia university"],
    "University of Pennsylvania": ["university of pennsylvania", "perelman"],
    "Sorbonne / Institut de la Vision (Paris)": ["institut de la vision", "sorbonne", "quinze-vingts"],
    "University of Manchester": ["university of manchester", "manchester royal eye"],
    "Ghent University": ["ghent university", "universiteit gent"],
    "University of Michigan": ["university of michigan", "kellogg eye"],
    "Harvard / Massachusetts Eye and Ear": ["massachusetts eye and ear", "harvard medical"],
    "Johns Hopkins University": ["johns hopkins", "wilmer eye"],
    "University of Iowa": ["university of iowa"],
    "Oregon Health & Science University": ["oregon health", "casey eye"],
    "National Eye Institute (NIH)": ["national eye institute"],
    "University of Oxford": ["university of oxford", "nuffield laboratory of ophthalmology"],
    "Baylor College of Medicine": ["baylor college"],
    "Ludwig Maximilian University Munich": ["ludwig-maximilians", "lmu munich", "munich"],
    "University of Leuven (KU Leuven)": ["ku leuven", "university of leuven", "leuven"],
}


def load_records() -> list[dict]:
    path = config.RAW_DIR / "pubmed_records.json"
    return json.loads(path.read_text())


def top_authors(records: list[dict], top_n: int = 20) -> list[dict]:
    counts: Counter[str] = Counter()
    for r in records:
        for a in r.get("authors", []):
            counts[a] += 1
    return [
        {"rank": i + 1, "author": a, "papers": c}
        for i, (a, c) in enumerate(counts.most_common(top_n))
    ]


def author_counter(records: list[dict]) -> Counter:
    counts: Counter[str] = Counter()
    for r in records:
        for a in r.get("authors", []):
            counts[a] += 1
    return counts


def highlight_author(records: list[dict], name: str) -> dict | None:
    """Where does `name` rank among all authors by paper count?"""
    counts = author_counter(records)
    ranking = counts.most_common()  # sorted desc
    for i, (a, c) in enumerate(ranking):
        if a == name:
            return {
                "author": a,
                "papers": c,
                "rank": i + 1,
                "total_authors": len(counts),
                "is_top": i == 0,
            }
    return None


def top_institutions(records: list[dict], top_n: int = 15) -> list[dict]:
    """Count papers crediting each canonical institution (once per paper)."""
    counts: Counter[str] = Counter()
    for r in records:
        affs = " || ".join(r.get("affiliations", [])).lower()
        if not affs:
            continue
        credited = set()
        for canonical, aliases in INSTITUTION_ALIASES.items():
            if any(alias in affs for alias in aliases):
                credited.add(canonical)
        for canonical in credited:
            counts[canonical] += 1
    return [
        {"rank": i + 1, "institution": inst, "papers": c}
        for i, (inst, c) in enumerate(counts.most_common(top_n))
    ]


def top_collaborations(records: list[dict], among_top: int = 100, top_n: int = 20) -> list[dict]:
    """Most frequent co-authorship pairs, restricted to the prolific core.

    Limiting to the top `among_top` authors keeps the result to the field's
    recurring collaborations rather than one-off large author lists.
    """
    counts = author_counter(records)
    core = {a for a, _ in counts.most_common(among_top)}
    pairs: Counter[tuple[str, str]] = Counter()
    for r in records:
        authors = sorted({a for a in r.get("authors", []) if a in core})
        for a, b in combinations(authors, 2):
            pairs[(a, b)] += 1
    return [
        {"a": a, "b": b, "papers": c}
        for (a, b), c in pairs.most_common(top_n)
        if c > 1  # a single shared paper isn't a "collaboration"
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--highlight", default="Michaelides M", help="Author to spotlight.")
    args = parser.parse_args()

    records = load_records()
    print(f"Loaded {len(records)} records.")

    result = {
        "top_authors": top_authors(records),
        "highlight": highlight_author(records, args.highlight),
        "top_institutions": top_institutions(records),
        "top_collaborations": top_collaborations(records),
        "with_affiliation": sum(1 for r in records if r.get("affiliations")),
        "total": len(records),
    }

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PROCESSED_DIR / "author_analysis.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"  wrote {out_path.relative_to(config.PROJECT_ROOT)}")

    h = result["highlight"]
    if h:
        print(f"\nHighlight: {h['author']} — rank #{h['rank']} of {h['total_authors']} "
              f"authors, {h['papers']} papers" + (" (TOP)" if h["is_top"] else ""))
    print("Top 3 authors:", [(a["author"], a["papers"]) for a in result["top_authors"][:3]])
    print("Top 3 institutions:", [(i["institution"], i["papers"]) for i in result["top_institutions"][:3]])


if __name__ == "__main__":
    main()

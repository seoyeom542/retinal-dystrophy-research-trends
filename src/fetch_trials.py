"""Collect inherited-retinal-dystrophy gene-therapy trials from ClinicalTrials.gov.

Companion data source to the PubMed analysis. Queries the ClinicalTrials.gov
API v2 for trials that pair an IRD-related condition with a gene-therapy
intervention, de-duplicates by NCT ID, and writes a compact table to
data/processed/clinical_trials.json for the website to render.

Usage:
    python src/fetch_trials.py
    python src/fetch_trials.py --max 50     # cap results per condition query
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request

import config

API_URL = "https://clinicaltrials.gov/api/v2/studies"

# IRD-related conditions to pair with a gene-therapy intervention filter.
# These mirror the disease landscape covered by the literature analysis.
CONDITIONS = [
    "inherited retinal dystrophy",
    "cone dystrophy",
    "cone-rod dystrophy",
    "Stargardt disease",
    "retinitis pigmentosa",
    "Leber congenital amaurosis",
    "achromatopsia",
    "choroideremia",
]
INTERVENTION = "gene therapy"


def _get(params: dict) -> dict:
    """Issue one GET request to the API and return parsed JSON."""
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _first(d: dict, *path, default=None):
    """Safely walk a nested dict path."""
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def parse_study(study: dict) -> dict:
    """Flatten one API study record into the fields we display."""
    ps = study.get("protocolSection", {})
    ident = ps.get("identificationModule", {})
    status = ps.get("statusModule", {})
    design = ps.get("designModule", {})
    conds = ps.get("conditionsModule", {})
    arms = ps.get("armsInterventionsModule", {})

    nct = ident.get("nctId", "")
    start_date = _first(status, "startDateStruct", "date", default="") or ""
    interventions = [
        i.get("name", "")
        for i in arms.get("interventions", [])
        if i.get("name")
    ]
    return {
        "nct_id": nct,
        "title": ident.get("briefTitle", ""),
        "status": status.get("overallStatus", ""),
        "start_date": start_date,
        "start_year": int(start_date[:4]) if start_date[:4].isdigit() else None,
        "phases": design.get("phases", []) or [],
        "study_type": design.get("studyType", ""),
        "conditions": conds.get("conditions", []) or [],
        "sponsor": _first(
            ps, "sponsorCollaboratorsModule", "leadSponsor", "name", default=""
        ),
        "interventions": interventions,
        "enrollment": _first(design, "enrollmentInfo", "count"),
        "url": f"https://clinicaltrials.gov/study/{nct}" if nct else "",
    }


def fetch_condition(condition: str, max_results: int) -> list[dict]:
    """Fetch trials for one condition + the gene-therapy intervention."""
    fields = [
        "protocolSection.identificationModule",
        "protocolSection.statusModule",
        "protocolSection.designModule",
        "protocolSection.conditionsModule",
        "protocolSection.armsInterventionsModule",
        "protocolSection.sponsorCollaboratorsModule",
    ]
    params = {
        "query.cond": condition,
        "query.intr": INTERVENTION,
        "pageSize": min(max_results, 100),
        "fields": "|".join(fields),
        "format": "json",
    }
    data = _get(params)
    return [parse_study(s) for s in data.get("studies", [])]


def merge(records: list[dict]) -> list[dict]:
    """De-duplicate by NCT ID; sort newest trials first."""
    by_id: dict[str, dict] = {}
    for rec in records:
        if rec["nct_id"] and rec["nct_id"] not in by_id:
            by_id[rec["nct_id"]] = rec
    out = list(by_id.values())
    # Newest start date first; undated trials sink to the bottom.
    out.sort(key=lambda r: (r["start_year"] or 0), reverse=True)
    return out


def summarize(trials: list[dict]) -> dict:
    """Headline counts for the page (status mix, active count)."""
    active_states = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
    status_counts: dict[str, int] = {}
    for t in trials:
        status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1
    return {
        "total": len(trials),
        "active": sum(1 for t in trials if t["status"] in active_states),
        "by_status": dict(sorted(status_counts.items(), key=lambda kv: kv[1], reverse=True)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max", type=int, default=100, help="Max results per condition query.")
    args = parser.parse_args()

    all_records: list[dict] = []
    for condition in CONDITIONS:
        print(f"[{condition}] querying gene-therapy trials...")
        try:
            recs = fetch_condition(condition, args.max)
        except Exception as exc:  # network hiccup on one query shouldn't sink the run
            print(f"  ! failed: {exc}")
            recs = []
        print(f"  {len(recs)} trials")
        all_records.extend(recs)
        time.sleep(0.3)  # be polite to the API

    trials = merge(all_records)
    summary = summarize(trials)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.PROCESSED_DIR / "clinical_trials.json"
    out_path.write_text(
        json.dumps({"summary": summary, "trials": trials}, ensure_ascii=False, indent=2)
    )

    print(
        f"\nDone. {summary['total']} unique trials "
        f"({summary['active']} active) -> {out_path.relative_to(config.PROJECT_ROOT)}"
    )
    print("Status mix:", summary["by_status"])


if __name__ == "__main__":
    main()

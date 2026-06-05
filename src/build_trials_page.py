"""Build the interactive clinical-trials page from the collected trial data.

Reads data/processed/clinical_trials.json and writes self-contained pages with
the trial data embedded inline (so they render on GitHub Pages with no fetch /
CORS / path concerns) plus client-side filtering by recruitment status:

  docs/clinical-trials.html        (Korean)
  docs/en/clinical-trials.html     (English)

Usage:
    python src/build_trials_page.py
"""
from __future__ import annotations

import json

import config

# Per-language UI strings and the relative path prefix back to site root.
LANGS = {
    "ko": {
        "out": config.PROJECT_ROOT / "docs" / "clinical-trials.html",
        "root": "",            # pages sit at docs/
        "en_href": "en/clinical-trials.html",
        "lang_label": "EN",
        "html_lang": "ko",
        "title": "임상시험 현황 — IRD Research Landscape",
        "meta": "유전성 망막이영양증 유전자치료 임상시험 현황. ClinicalTrials.gov 데이터 기반 인터랙티브 목록.",
        "nav": {"dashboard": "대시보드", "trials": "임상시험", "basics": "기초 개념", "paper": "논문 번역"},
        "subtitle": "유전성 망막이영양증 유전자치료",
        "h1": "임상시험 현황",
        "hero_desc": "문헌에서 본 연구 동향이 실제 환자 치료로 이어지는 현장입니다. ClinicalTrials.gov에 등록된 유전성 망막이영양증 <strong>유전자치료 임상시험</strong>을 모았습니다.",
        "stat_total": "총 임상시험", "stat_active": "진행 중",
        "stat_years": "시작 연도 범위", "stat_sponsors": "주관 기관 수",
        "list_h2": "임상시험 목록",
        "list_lead": "상태별로 필터링할 수 있습니다. 각 시험명을 클릭하면 ClinicalTrials.gov 원문으로 이동합니다. 최신 시작일 순으로 정렬되어 있습니다.",
        "f_all": "전체", "f_recruiting": "모집 중", "f_active": "진행 중", "f_completed": "완료",
        "th_title": "시험명 / 주관 기관", "th_status": "상태", "th_phase": "임상단계", "th_start": "시작",
        "empty": "해당 조건의 임상시험이 없습니다.",
        "note": '출처: <a href="https://clinicaltrials.gov/" target="_blank" rel="noopener">ClinicalTrials.gov</a> API v2 · 데이터 수집 2026년 6월. 본 목록은 정보 제공 목적이며 의학적 조언이 아닙니다.',
        "foot_back": "← 대시보드로 돌아가기",
        "foot_note": "교육·연구 목적의 문헌 분석 프로젝트",
        "foot_contact": "문의",
        "obs": "관찰/기타",
        "status_ko": {
            "RECRUITING": "모집 중", "NOT_YET_RECRUITING": "모집 예정",
            "ENROLLING_BY_INVITATION": "초청 등록", "ACTIVE_NOT_RECRUITING": "진행 중(모집종료)",
            "COMPLETED": "완료", "TERMINATED": "중단", "WITHDRAWN": "철회", "SUSPENDED": "보류",
        },
    },
    "en": {
        "out": config.PROJECT_ROOT / "docs" / "en" / "clinical-trials.html",
        "root": "../",         # pages sit at docs/en/
        "en_href": "../clinical-trials.html",
        "lang_label": "한국어",
        "html_lang": "en",
        "title": "Clinical Trials — IRD Research Landscape",
        "meta": "Gene-therapy clinical trials for inherited retinal dystrophy. Interactive list built on ClinicalTrials.gov data.",
        "nav": {"dashboard": "Dashboard", "trials": "Clinical trials", "basics": "Background", "paper": "Source paper"},
        "subtitle": "Gene therapy for inherited retinal dystrophy",
        "h1": "Clinical Trials",
        "hero_desc": "Where the research trends seen in the literature turn into patient care. A curated set of <strong>gene-therapy clinical trials</strong> for inherited retinal dystrophy, registered on ClinicalTrials.gov.",
        "stat_total": "Total trials", "stat_active": "Active",
        "stat_years": "Start-year range", "stat_sponsors": "Lead sponsors",
        "list_h2": "Trial list",
        "list_lead": "Filter by recruitment status. Click a trial title to open its ClinicalTrials.gov record. Sorted by most recent start date.",
        "f_all": "All", "f_recruiting": "Recruiting", "f_active": "Active", "f_completed": "Completed",
        "th_title": "Trial / lead sponsor", "th_status": "Status", "th_phase": "Phase", "th_start": "Start",
        "empty": "No trials match this filter.",
        "note": 'Source: <a href="https://clinicaltrials.gov/" target="_blank" rel="noopener">ClinicalTrials.gov</a> API v2 · collected June 2026. For information only; not medical advice.',
        "foot_back": "← Back to dashboard",
        "foot_note": "An educational / research literature-analysis project",
        "foot_contact": "Contact",
        "obs": "Observational / other",
        "status_ko": {
            "RECRUITING": "Recruiting", "NOT_YET_RECRUITING": "Not yet recruiting",
            "ENROLLING_BY_INVITATION": "Enrolling by invitation", "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
            "COMPLETED": "Completed", "TERMINATED": "Terminated", "WITHDRAWN": "Withdrawn", "SUSPENDED": "Suspended",
        },
    },
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="{html_lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <meta name="description" content="{meta}" />
  <link rel="stylesheet" href="{root}style.css" />
</head>
<body>

  <nav class="nav">
    <div class="nav-inner">
      <a class="nav-brand" href="{root}index.html">🔬 IRD Research Landscape</a>
      <div class="nav-links">
        <a href="{root}index.html#dashboard">{nav_dashboard}</a>
        <a href="clinical-trials.html">{nav_trials}</a>
        <a href="{root}about-cone-dystrophy.html">{nav_basics}</a>
        {paper_link}
        <a href="{en_href}" class="lang-toggle">{lang_label}</a>
      </div>
    </div>
  </nav>

  <header class="hero">
    <p class="subtitle">{subtitle}</p>
    <h1>{h1}</h1>
    <p class="desc">{hero_desc}</p>
  </header>

  <section class="stats" aria-label="summary">
    <div class="stat"><div class="num">{total}</div><div class="label">{stat_total}</div></div>
    <div class="stat"><div class="num">{active}</div><div class="label">{stat_active}</div></div>
    <div class="stat"><div class="num">{year_range}</div><div class="label">{stat_years}</div></div>
    <div class="stat"><div class="num">{sponsors}</div><div class="label">{stat_sponsors}</div></div>
  </section>

  <main class="section">
    <h2>{list_h2}</h2>
    <p class="lead">{list_lead}</p>

    <div class="trials-controls" id="filters">
      <button data-filter="all" class="active">{f_all} <span id="c-all"></span></button>
      <button data-filter="recruiting">{f_recruiting} <span id="c-recruiting"></span></button>
      <button data-filter="active">{f_active} <span id="c-active"></span></button>
      <button data-filter="completed">{f_completed} <span id="c-completed"></span></button>
    </div>

    <div class="chart-card" style="overflow-x:auto">
      <table class="trials-table">
        <thead>
          <tr>
            <th>{th_title}</th>
            <th>{th_status}</th>
            <th>{th_phase}</th>
            <th>{th_start}</th>
          </tr>
        </thead>
        <tbody id="trials-body"></tbody>
      </table>
      <div class="trials-empty" id="empty" style="display:none">{empty}</div>
    </div>
    <p class="chart-note">{note}</p>
  </main>

  <footer class="footer">
    <p><a href="{root}index.html">{foot_back}</a></p>
    <p>{foot_note}</p>
    <p>{foot_contact} · <a href="mailto:seoyeom542@gmail.com">seoyeom542@gmail.com</a></p>
  </footer>

  <script>
    const TRIALS = {trials_json};
    const STATUS_LABEL = {status_label_json};
    const OBS = {obs_json};
    const STATUS_META = {{
      RECRUITING:              {{cls: "st-recruiting", bucket: ["recruiting", "active"]}},
      NOT_YET_RECRUITING:      {{cls: "st-recruiting", bucket: ["recruiting", "active"]}},
      ENROLLING_BY_INVITATION: {{cls: "st-recruiting", bucket: ["recruiting", "active"]}},
      ACTIVE_NOT_RECRUITING:   {{cls: "st-active", bucket: ["active"]}},
      COMPLETED:               {{cls: "st-completed", bucket: ["completed"]}},
      TERMINATED:              {{cls: "st-terminated", bucket: []}},
      WITHDRAWN:               {{cls: "st-terminated", bucket: []}},
      SUSPENDED:               {{cls: "st-terminated", bucket: []}},
    }};
    function statusInfo(s) {{
      const meta = STATUS_META[s] || {{cls: "st-other", bucket: []}};
      const label = STATUS_LABEL[s] || (s || "").replaceAll("_", " ");
      return {{ko: label, cls: meta.cls, bucket: meta.bucket}};
    }}
    function phaseLabel(phases) {{
      if (!phases || !phases.length) return '<span class="t-meta">' + OBS + '</span>';
      return phases.map(p => '<span class="phase-chip">' + p.replace("PHASE", "P").replace("EARLY_P1", "Early P1") + '</span>').join(" ");
    }}

    const body = document.getElementById("trials-body");
    const empty = document.getElementById("empty");

    function render(filter) {{
      const rows = TRIALS.filter(t => filter === "all" ? true : statusInfo(t.status).bucket.includes(filter));
      body.innerHTML = rows.map(t => {{
        const si = statusInfo(t.status);
        const sponsor = t.sponsor ? '<div class="t-meta">' + t.sponsor + '</div>' : "";
        const link = t.url ? '<a href="' + t.url + '" target="_blank" rel="noopener">' + t.title + '</a>' : t.title;
        return '<tr>' +
          '<td class="t-title">' + link + sponsor + '</td>' +
          '<td><span class="badge-status ' + si.cls + '">' + si.ko + '</span></td>' +
          '<td>' + phaseLabel(t.phases) + '</td>' +
          '<td>' + (t.start_year || "\\u2014") + '</td>' +
        '</tr>';
      }}).join("");
      empty.style.display = rows.length ? "none" : "block";
    }}

    const count = f => TRIALS.filter(t => f === "all" || statusInfo(t.status).bucket.includes(f)).length;
    ["all", "recruiting", "active", "completed"].forEach(f => {{
      document.getElementById("c-" + f).textContent = "(" + count(f) + ")";
    }});
    document.getElementById("filters").addEventListener("click", e => {{
      const btn = e.target.closest("button");
      if (!btn) return;
      document.querySelectorAll("#filters button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      render(btn.dataset.filter);
    }});
    render("all");
  </script>

</body>
</html>
"""


def build(lang: str, L: dict, trials: list, summary: dict) -> None:
    years = [t["start_year"] for t in trials if t["start_year"]]
    year_range = f"{min(years)}–{max(years)}" if years else "—"
    sponsors = len({t["sponsor"] for t in trials if t["sponsor"]})

    # The source-paper nav entry links to the KO translation (ko) or the DOI (en).
    if lang == "ko":
        paper_link = f'<a href="{L["root"]}paper/index.html">{L["nav"]["paper"]}</a>'
    else:
        paper_link = f'<a href="https://doi.org/10.1136/bjophthalmol-2018-313278" target="_blank" rel="noopener">{L["nav"]["paper"]}</a>'

    html = PAGE_TEMPLATE.format(
        html_lang=L["html_lang"],
        title=L["title"],
        meta=L["meta"],
        root=L["root"],
        nav_dashboard=L["nav"]["dashboard"],
        nav_trials=L["nav"]["trials"],
        nav_basics=L["nav"]["basics"],
        paper_link=paper_link,
        en_href=L["en_href"],
        lang_label=L["lang_label"],
        subtitle=L["subtitle"],
        h1=L["h1"],
        hero_desc=L["hero_desc"],
        total=summary["total"],
        active=summary["active"],
        year_range=year_range,
        sponsors=sponsors,
        stat_total=L["stat_total"],
        stat_active=L["stat_active"],
        stat_years=L["stat_years"],
        stat_sponsors=L["stat_sponsors"],
        list_h2=L["list_h2"],
        list_lead=L["list_lead"],
        f_all=L["f_all"],
        f_recruiting=L["f_recruiting"],
        f_active=L["f_active"],
        f_completed=L["f_completed"],
        th_title=L["th_title"],
        th_status=L["th_status"],
        th_phase=L["th_phase"],
        th_start=L["th_start"],
        empty=L["empty"],
        note=L["note"],
        foot_back=L["foot_back"],
        foot_note=L["foot_note"],
        foot_contact=L["foot_contact"],
        trials_json=json.dumps(trials, ensure_ascii=False),
        status_label_json=json.dumps(L["status_ko"], ensure_ascii=False),
        obs_json=json.dumps(L["obs"], ensure_ascii=False),
    )
    L["out"].parent.mkdir(parents=True, exist_ok=True)
    L["out"].write_text(html)
    print(f"  wrote {L['out'].relative_to(config.PROJECT_ROOT)} ({summary['total']} trials)")


def main() -> None:
    data = json.loads((config.PROCESSED_DIR / "clinical_trials.json").read_text())
    for lang, L in LANGS.items():
        build(lang, L, data["trials"], data["summary"])


if __name__ == "__main__":
    main()

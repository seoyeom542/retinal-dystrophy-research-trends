"""Build the interactive clinical-trials page from the collected trial data.

Reads data/processed/clinical_trials.json and writes a self-contained
docs/clinical-trials.html with the trial data embedded inline (so it renders on
GitHub Pages with no fetch / CORS / path concerns) plus client-side filtering
by recruitment status.

Usage:
    python src/build_trials_page.py
"""
from __future__ import annotations

import json

import config

OUT_PATH = config.PROJECT_ROOT / "docs" / "clinical-trials.html"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>임상시험 현황 — IRD Research Landscape</title>
  <meta name="description" content="유전성 망막이영양증 유전자치료 임상시험 현황. ClinicalTrials.gov 데이터 기반 인터랙티브 목록." />
  <link rel="stylesheet" href="style.css" />
</head>
<body>

  <nav class="nav">
    <div class="nav-inner">
      <a class="nav-brand" href="index.html">🔬 IRD Research Landscape</a>
      <div class="nav-links">
        <a href="index.html#dashboard">대시보드</a>
        <a href="clinical-trials.html">임상시험</a>
        <a href="about-cone-dystrophy.html">기초 개념</a>
        <a href="paper/index.html">논문 번역</a>
      </div>
    </div>
  </nav>

  <header class="hero">
    <p class="subtitle">유전성 망막이영양증 유전자치료</p>
    <h1>임상시험 현황</h1>
    <p class="desc">
      문헌에서 본 연구 동향이 실제 환자 치료로 이어지는 현장입니다. ClinicalTrials.gov에
      등록된 유전성 망막이영양증 <strong>유전자치료 임상시험</strong>을 모았습니다.
    </p>
  </header>

  <section class="stats" aria-label="임상시험 요약">
    <div class="stat"><div class="num">__TOTAL__</div><div class="label">총 임상시험</div></div>
    <div class="stat"><div class="num">__ACTIVE__</div><div class="label">진행 중</div></div>
    <div class="stat"><div class="num">__YEAR_RANGE__</div><div class="label">시작 연도 범위</div></div>
    <div class="stat"><div class="num">__SPONSORS__</div><div class="label">주관 기관 수</div></div>
  </section>

  <main class="section">
    <h2>임상시험 목록</h2>
    <p class="lead">
      상태별로 필터링할 수 있습니다. 각 시험명을 클릭하면 ClinicalTrials.gov 원문으로
      이동합니다. 최신 시작일 순으로 정렬되어 있습니다.
    </p>

    <div class="trials-controls" id="filters">
      <button data-filter="all" class="active">전체 <span id="c-all"></span></button>
      <button data-filter="recruiting">모집 중 <span id="c-recruiting"></span></button>
      <button data-filter="active">진행 중 <span id="c-active"></span></button>
      <button data-filter="completed">완료 <span id="c-completed"></span></button>
    </div>

    <div class="chart-card" style="overflow-x:auto">
      <table class="trials-table">
        <thead>
          <tr>
            <th>시험명 / 주관 기관</th>
            <th>상태</th>
            <th>임상단계</th>
            <th>시작</th>
          </tr>
        </thead>
        <tbody id="trials-body"></tbody>
      </table>
      <div class="trials-empty" id="empty" style="display:none">해당 조건의 임상시험이 없습니다.</div>
    </div>
    <p class="chart-note">
      출처: <a href="https://clinicaltrials.gov/" target="_blank" rel="noopener">ClinicalTrials.gov</a>
      API v2 · 데이터 수집 2026년 6월. 본 목록은 정보 제공 목적이며 의학적 조언이 아닙니다.
    </p>
  </main>

  <footer class="footer">
    <p><a href="index.html">← 대시보드로 돌아가기</a></p>
    <p>교육·연구 목적의 문헌 분석 프로젝트</p>
    <p>문의 · <a href="mailto:seoyeom542@gmail.com">seoyeom542@gmail.com</a></p>
  </footer>

  <script>
    const TRIALS = __TRIALS_JSON__;

    // Map raw API status -> {korean label, css class, filter bucket}.
    const STATUS = {
      RECRUITING:               {ko: "모집 중", cls: "st-recruiting", bucket: ["recruiting", "active"]},
      NOT_YET_RECRUITING:       {ko: "모집 예정", cls: "st-recruiting", bucket: ["recruiting", "active"]},
      ENROLLING_BY_INVITATION:  {ko: "초청 등록", cls: "st-recruiting", bucket: ["recruiting", "active"]},
      ACTIVE_NOT_RECRUITING:    {ko: "진행 중(모집종료)", cls: "st-active", bucket: ["active"]},
      COMPLETED:                {ko: "완료", cls: "st-completed", bucket: ["completed"]},
      TERMINATED:               {ko: "중단", cls: "st-terminated", bucket: []},
      WITHDRAWN:                {ko: "철회", cls: "st-terminated", bucket: []},
      SUSPENDED:                {ko: "보류", cls: "st-terminated", bucket: []},
    };
    function statusInfo(s) {
      return STATUS[s] || {ko: (s || "기타").replaceAll("_", " "), cls: "st-other", bucket: []};
    }
    function phaseLabel(phases) {
      if (!phases || !phases.length) return '<span class="t-meta">관찰/기타</span>';
      return phases.map(p => '<span class="phase-chip">' + p.replace("PHASE", "P").replace("EARLY_P1", "Early P1") + '</span>').join(" ");
    }

    const body = document.getElementById("trials-body");
    const empty = document.getElementById("empty");

    function render(filter) {
      const rows = TRIALS.filter(t => {
        if (filter === "all") return true;
        return statusInfo(t.status).bucket.includes(filter);
      });
      body.innerHTML = rows.map(t => {
        const si = statusInfo(t.status);
        const sponsor = t.sponsor ? '<div class="t-meta">' + t.sponsor + '</div>' : "";
        const link = t.url ? '<a href="' + t.url + '" target="_blank" rel="noopener">' + t.title + '</a>' : t.title;
        return '<tr>' +
          '<td class="t-title">' + link + sponsor + '</td>' +
          '<td><span class="badge-status ' + si.cls + '">' + si.ko + '</span></td>' +
          '<td>' + phaseLabel(t.phases) + '</td>' +
          '<td>' + (t.start_year || "—") + '</td>' +
        '</tr>';
      }).join("");
      empty.style.display = rows.length ? "none" : "block";
    }

    // Filter button counts + wiring.
    const count = f => TRIALS.filter(t => f === "all" || statusInfo(t.status).bucket.includes(f)).length;
    ["all", "recruiting", "active", "completed"].forEach(f => {
      document.getElementById("c-" + f).textContent = "(" + count(f) + ")";
    });
    document.getElementById("filters").addEventListener("click", e => {
      const btn = e.target.closest("button");
      if (!btn) return;
      document.querySelectorAll("#filters button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      render(btn.dataset.filter);
    });

    render("all");
  </script>

</body>
</html>
"""


def main() -> None:
    data = json.loads((config.PROCESSED_DIR / "clinical_trials.json").read_text())
    trials = data["trials"]
    summary = data["summary"]

    years = [t["start_year"] for t in trials if t["start_year"]]
    year_range = f"{min(years)}–{max(years)}" if years else "—"
    sponsors = len({t["sponsor"] for t in trials if t["sponsor"]})

    html = (
        PAGE_TEMPLATE.replace("__TOTAL__", str(summary["total"]))
        .replace("__ACTIVE__", str(summary["active"]))
        .replace("__YEAR_RANGE__", year_range)
        .replace("__SPONSORS__", str(sponsors))
        # Embed compact JSON (the page only needs the per-trial fields it renders).
        .replace("__TRIALS_JSON__", json.dumps(trials, ensure_ascii=False))
    )
    OUT_PATH.write_text(html)
    print(
        f"Wrote {OUT_PATH.relative_to(config.PROJECT_ROOT)} "
        f"({summary['total']} trials, {sponsors} sponsors, {year_range})"
    )


if __name__ == "__main__":
    main()

"""Build interactive Plotly charts from the processed analysis tables.

Stage 3 of the pipeline. Reads data/processed/*.json and writes, per language:

  docs/charts/<lang>/yearly_trend.html        publication counts over time
  docs/charts/<lang>/gene_mentions.html       top genes (horizontal bar)
  docs/charts/<lang>/treatment_totals.html    research volume per modality
  docs/charts/<lang>/treatment_over_time.html modality trends (stacked area)
  docs/charts/<lang>/top_journals.html        leading journals

Korean charts go to docs/charts/ko/ and English to docs/charts/en/. The word
cloud (language-neutral) is written once to docs/assets/.

Each chart is a self-contained HTML page (Plotly.js from CDN) so it works both
on its own and embedded via <iframe> in the dashboards.

Usage:
    python src/visualize.py
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any

import plotly.graph_objects as go
import plotly.io as pio

import config

CHARTS_DIR = config.PROJECT_ROOT / "docs" / "charts"
ASSETS_DIR = config.PROJECT_ROOT / "docs" / "assets"

# A calm, clinical palette — teal/blue with warm accents.
PALETTE = ["#1f7a8c", "#bfd7ea", "#e1701a", "#022b3a", "#5fa8d3",
           "#c46d5e", "#2a9d8f", "#8d99ae", "#e9c46a", "#6a4c93"]

# All user-facing chart strings, keyed by language.
STRINGS: dict[str, dict[str, Any]] = {
    "ko": {
        "queries": {
            "cone_dystrophy": "추체이영양증 (Cone dystrophy)",
            "inherited_retinal_dystrophy": "유전성 망막이영양증 (IRD)",
            "retinal_gene_therapy": "망막 유전자치료 (Gene therapy)",
        },
        "yearly_title": "연도별 논문 발행 추이",
        "yearly_x": "발행 연도",
        "yearly_y": "논문 수",
        "all": "전체 (All)",
        "gene_title": "가장 많이 언급된 유전자 Top {n}",
        "gene_x": "언급된 논문 수",
        "gene_hover": "<b>%{y}</b><br>언급 논문 수: %{x}<extra></extra>",
        "treat_title": "치료 방법별 연구 비중",
        "treat_y": "논문 수",
        "treat_hover": "<b>%{x}</b><br>논문 수: %{y}<extra></extra>",
        "treat_time_title": "치료 방법별 연구 동향 (연도별 누적)",
        "treat_time_x": "발행 연도",
        "treat_unit": "편",
        "journal_title": "주요 저널 Top {n}",
        "journal_x": "논문 수",
        "journal_hover": "<b>%{y}</b><br>논문 수: %{x}<extra></extra>",
        "author_title": "가장 많이 출판한 저자 Top {n}",
        "author_x": "논문 수",
        "author_hover": "<b>%{y}</b><br>논문 수: %{x}<extra></extra>",
        "inst_title": "가장 활발한 연구 기관 Top {n}",
        "inst_x": "논문 수",
        "inst_hover": "<b>%{y}</b><br>논문 수: %{x}<extra></extra>",
    },
    "en": {
        "queries": {
            "cone_dystrophy": "Cone dystrophy",
            "inherited_retinal_dystrophy": "Inherited retinal dystrophy",
            "retinal_gene_therapy": "Retinal gene therapy",
        },
        "yearly_title": "Publications per Year",
        "yearly_x": "Publication year",
        "yearly_y": "Publications",
        "all": "All",
        "gene_title": "Most-Mentioned Genes (Top {n})",
        "gene_x": "Number of publications",
        "gene_hover": "<b>%{y}</b><br>Publications: %{x}<extra></extra>",
        "treat_title": "Research Volume by Treatment Modality",
        "treat_y": "Publications",
        "treat_hover": "<b>%{x}</b><br>Publications: %{y}<extra></extra>",
        "treat_time_title": "Treatment Modalities over Time (stacked)",
        "treat_time_x": "Publication year",
        "treat_unit": "",
        "journal_title": "Leading Journals (Top {n})",
        "journal_x": "Number of publications",
        "journal_hover": "<b>%{y}</b><br>Publications: %{x}<extra></extra>",
        "author_title": "Most Prolific Authors (Top {n})",
        "author_x": "Number of publications",
        "author_hover": "<b>%{y}</b><br>Publications: %{x}<extra></extra>",
        "inst_title": "Most Active Research Institutions (Top {n})",
        "inst_x": "Number of publications",
        "inst_hover": "<b>%{y}</b><br>Publications: %{x}<extra></extra>",
    },
}

# Author to spotlight (accent-coloured) in the author chart.
HIGHLIGHT_AUTHOR = "Michaelides M"

# Horizontal legend placed BELOW the plot, clear of the title. Putting it above
# (y>1) makes the clickable legend overlap the chart title, hiding it.
LEGEND_BELOW = dict(orientation="h", yanchor="top", y=-0.28, x=0.5, xanchor="center")


def _load(name: str) -> Any:
    return json.loads((config.PROCESSED_DIR / name).read_text())


def _base_layout(title: str, **kwargs) -> dict:
    """Shared layout: consistent fonts, margins, and a light template."""
    layout = dict(
        title=dict(text=title, font=dict(size=20, color="#022b3a")),
        template="plotly_white",
        font=dict(family="-apple-system, 'Segoe UI', Roboto, sans-serif", size=13),
        margin=dict(l=70, r=30, t=60, b=50),
        hovermode="closest",
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    layout.update(kwargs)
    return layout


def _save(fig: go.Figure, lang: str, name: str) -> None:
    out_dir = CHARTS_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    pio.write_html(
        fig,
        file=str(path),
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )
    print(f"  wrote {path.relative_to(config.PROJECT_ROOT)}")


def chart_yearly_trend(lang: str, s: dict) -> None:
    """Line chart: overall publications per year + per-query breakdown."""
    data = _load("yearly_counts.json")
    fig = go.Figure()

    overall = data["overall"]
    years = sorted(int(y) for y in overall)
    fig.add_trace(
        go.Scatter(
            x=years,
            y=[overall[str(y)] for y in years],
            mode="lines+markers",
            name=s["all"],
            line=dict(color=PALETTE[3], width=3),
            marker=dict(size=6),
        )
    )
    for i, (key, counts) in enumerate(data["by_query"].items()):
        ys = sorted(int(y) for y in counts)
        fig.add_trace(
            go.Scatter(
                x=ys,
                y=[counts[str(y)] for y in ys],
                mode="lines",
                name=s["queries"].get(key, key),
                line=dict(color=PALETTE[i % len(PALETTE)], width=2, dash="dot"),
            )
        )
    fig.update_layout(
        **_base_layout(
            s["yearly_title"],
            xaxis_title=s["yearly_x"],
            yaxis_title=s["yearly_y"],
            legend=LEGEND_BELOW,
            margin=dict(l=70, r=30, t=60, b=95),
        )
    )
    _save(fig, lang, "yearly_trend.html")


def chart_gene_mentions(lang: str, s: dict, top_n: int = 15) -> None:
    """Horizontal bar: most-mentioned genes."""
    genes = _load("gene_mentions.json")
    items = list(genes.items())[:top_n][::-1]  # reversed so largest is on top
    names = [g for g, _ in items]
    counts = [c for _, c in items]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=names,
            orientation="h",
            marker=dict(color=counts, colorscale="Teal", showscale=False),
            text=counts,
            textposition="outside",
            hovertemplate=s["gene_hover"],
        )
    )
    fig.update_layout(
        **_base_layout(
            s["gene_title"].format(n=top_n),
            xaxis_title=s["gene_x"],
            yaxis_title="",
        )
    )
    _save(fig, lang, "gene_mentions.html")


def chart_treatment_totals(lang: str, s: dict) -> None:
    """Bar: research volume per treatment modality."""
    totals = _load("treatment_trends.json")["totals"]
    names = list(totals)
    counts = [totals[n] for n in names]
    fig = go.Figure(
        go.Bar(
            x=names,
            y=counts,
            marker=dict(color=PALETTE[:len(names)]),
            text=counts,
            textposition="outside",
            hovertemplate=s["treat_hover"],
        )
    )
    fig.update_layout(
        **_base_layout(
            s["treat_title"],
            xaxis_title="",
            yaxis_title=s["treat_y"],
        )
    )
    _save(fig, lang, "treatment_totals.html")


def chart_treatment_over_time(lang: str, s: dict, start_year: int = 2005) -> None:
    """Stacked area: each modality's publication count over time."""
    by_year = _load("treatment_trends.json")["by_year"]
    all_years = sorted(
        {int(y) for counts in by_year.values() for y in counts if int(y) >= start_year}
    )
    fig = go.Figure()
    for i, (modality, counts) in enumerate(by_year.items()):
        fig.add_trace(
            go.Scatter(
                x=all_years,
                y=[counts.get(str(y), 0) for y in all_years],
                mode="lines",
                name=modality,
                stackgroup="one",
                line=dict(width=0.5, color=PALETTE[i % len(PALETTE)]),
                hovertemplate="%{y}" + s["treat_unit"] + "<extra>" + modality + "</extra>",
            )
        )
    fig.update_layout(
        **_base_layout(
            s["treat_time_title"],
            xaxis_title=s["treat_time_x"],
            yaxis_title=s["treat_y"],
            legend=LEGEND_BELOW,
            margin=dict(l=70, r=30, t=60, b=120),
        )
    )
    _save(fig, lang, "treatment_over_time.html")


def chart_top_journals(lang: str, s: dict, top_n: int = 12) -> None:
    """Horizontal bar: leading journals."""
    journals = _load("top_journals.json")
    items = list(journals.items())[:top_n][::-1]
    names = [j for j, _ in items]
    counts = [c for _, c in items]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=names,
            orientation="h",
            marker=dict(color=PALETTE[0]),
            text=counts,
            textposition="outside",
            hovertemplate=s["journal_hover"],
        )
    )
    fig.update_layout(
        **_base_layout(
            s["journal_title"].format(n=top_n),
            xaxis_title=s["journal_x"],
            yaxis_title="",
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    _save(fig, lang, "top_journals.html")


def chart_top_authors(lang: str, s: dict, top_n: int = 12) -> None:
    """Horizontal bar: most prolific authors, spotlighting one researcher."""
    data = _load("author_analysis.json")
    items = data["top_authors"][:top_n][::-1]  # reversed so #1 sits on top
    names = [a["author"] for a in items]
    counts = [a["papers"] for a in items]
    # Accent colour for the spotlighted author, teal for everyone else.
    colors = [PALETTE[2] if n == HIGHLIGHT_AUTHOR else PALETTE[0] for n in names]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=names,
            orientation="h",
            marker=dict(color=colors),
            text=counts,
            textposition="outside",
            hovertemplate=s["author_hover"],
        )
    )
    fig.update_layout(
        **_base_layout(
            s["author_title"].format(n=top_n),
            xaxis_title=s["author_x"],
            yaxis_title="",
        )
    )
    _save(fig, lang, "top_authors.html")


def chart_top_institutions(lang: str, s: dict, top_n: int = 10) -> None:
    """Horizontal bar: most active institutions."""
    data = _load("author_analysis.json")
    items = data["top_institutions"][:top_n][::-1]
    names = [i["institution"] for i in items]
    counts = [i["papers"] for i in items]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=names,
            orientation="h",
            marker=dict(color=counts, colorscale="Teal", showscale=False),
            text=counts,
            textposition="outside",
            hovertemplate=s["inst_hover"],
        )
    )
    fig.update_layout(
        **_base_layout(
            s["inst_title"].format(n=top_n),
            xaxis_title=s["inst_x"],
            yaxis_title="",
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    _save(fig, lang, "top_institutions.html")


def make_wordcloud() -> None:
    """Render a keyword word cloud PNG (language-neutral) from raw keywords."""
    from wordcloud import WordCloud

    records = json.loads((config.RAW_DIR / "pubmed_records.json").read_text())
    stop_terms = {
        "humans", "human", "animals", "female", "male", "adult", "aged",
        "middle aged", "child", "adolescent", "young adult", "mice",
        "retrospective studies", "treatment outcome", "follow-up studies",
    }
    freqs: Counter[str] = Counter()
    for rec in records:
        for kw in rec.get("keywords", []):
            term = kw.strip()
            if term and term.lower() not in stop_terms and len(term) > 2:
                freqs[term] += 1

    if not freqs:
        print("  (no keywords found; skipping word cloud)")
        return

    wc = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        colormap="viridis",
        max_words=120,
        prefer_horizontal=0.9,
    ).generate_from_frequencies(freqs)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    path = ASSETS_DIR / "keyword_wordcloud.png"
    wc.to_file(str(path))
    print(f"  wrote {path.relative_to(config.PROJECT_ROOT)}")


def main() -> None:
    for lang, s in STRINGS.items():
        print(f"Building {lang} charts...")
        chart_yearly_trend(lang, s)
        chart_gene_mentions(lang, s)
        chart_treatment_totals(lang, s)
        chart_treatment_over_time(lang, s)
        chart_top_journals(lang, s)
        chart_top_authors(lang, s)
        chart_top_institutions(lang, s)
    print("Building language-neutral word cloud...")
    make_wordcloud()
    print("\nDone. Charts in docs/charts/<lang>/, word cloud in docs/assets/.")


if __name__ == "__main__":
    main()

"""Build interactive Plotly charts from the processed analysis tables.

Stage 3 of the pipeline. Reads data/processed/*.json and writes:

  docs/charts/yearly_trend.html        publication counts over time
  docs/charts/gene_mentions.html       top genes (horizontal bar)
  docs/charts/treatment_totals.html    research volume per modality
  docs/charts/treatment_over_time.html modality trends (stacked area)
  docs/charts/top_journals.html        leading journals
  docs/assets/keyword_wordcloud.png    keyword frequency word cloud

Each chart is a self-contained HTML page (Plotly.js from CDN) so it works both
on its own and embedded via <iframe> in the GitHub Pages dashboard.

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

# Human-readable labels for the internal query keys.
QUERY_LABELS = {
    "cone_dystrophy": "추체이영양증 (Cone dystrophy)",
    "inherited_retinal_dystrophy": "유전성 망막이영양증 (IRD)",
    "retinal_gene_therapy": "망막 유전자치료 (Gene therapy)",
}


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


def _save(fig: go.Figure, name: str) -> None:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CHARTS_DIR / name
    pio.write_html(
        fig,
        file=str(path),
        include_plotlyjs="cdn",
        full_html=True,
        config={"displayModeBar": False, "responsive": True},
    )
    print(f"  wrote {path.relative_to(config.PROJECT_ROOT)}")


def chart_yearly_trend() -> None:
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
            name="전체 (All)",
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
                name=QUERY_LABELS.get(key, key),
                line=dict(color=PALETTE[i % len(PALETTE)], width=2, dash="dot"),
            )
        )
    fig.update_layout(
        **_base_layout(
            "연도별 논문 발행 추이",
            xaxis_title="발행 연도",
            yaxis_title="논문 수",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
    )
    _save(fig, "yearly_trend.html")


def chart_gene_mentions(top_n: int = 15) -> None:
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
            hovertemplate="<b>%{y}</b><br>언급 논문 수: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base_layout(
            f"가장 많이 언급된 유전자 Top {top_n}",
            xaxis_title="언급된 논문 수",
            yaxis_title="",
        )
    )
    _save(fig, "gene_mentions.html")


def chart_treatment_totals() -> None:
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
            hovertemplate="<b>%{x}</b><br>논문 수: %{y}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base_layout(
            "치료 방법별 연구 비중",
            xaxis_title="",
            yaxis_title="논문 수",
        )
    )
    _save(fig, "treatment_totals.html")


def chart_treatment_over_time(start_year: int = 2005) -> None:
    """Stacked area: each modality's publication count over time."""
    by_year = _load("treatment_trends.json")["by_year"]
    # Union of all years across modalities, bounded to keep the x-axis clean.
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
                hovertemplate="%{y}편<extra>" + modality + "</extra>",
            )
        )
    fig.update_layout(
        **_base_layout(
            "치료 방법별 연구 동향 (연도별 누적)",
            xaxis_title="발행 연도",
            yaxis_title="논문 수",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
    )
    _save(fig, "treatment_over_time.html")


def chart_top_journals(top_n: int = 12) -> None:
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
            hovertemplate="<b>%{y}</b><br>논문 수: %{x}<extra></extra>",
        )
    )
    fig.update_layout(
        **_base_layout(
            f"주요 저널 Top {top_n}",
            xaxis_title="논문 수",
            yaxis_title="",
        ),
        yaxis=dict(tickfont=dict(size=11)),
    )
    _save(fig, "top_journals.html")


def make_wordcloud() -> None:
    """Render a keyword word cloud PNG from the raw records' keywords."""
    from wordcloud import WordCloud

    records = json.loads((config.RAW_DIR / "pubmed_records.json").read_text())
    # Down-weight near-universal MeSH boilerplate so topical terms stand out.
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
    print("Building interactive charts...")
    chart_yearly_trend()
    chart_gene_mentions()
    chart_treatment_totals()
    chart_treatment_over_time()
    chart_top_journals()
    make_wordcloud()
    print("\nDone. Charts in docs/charts/, assets in docs/assets/.")


if __name__ == "__main__":
    main()

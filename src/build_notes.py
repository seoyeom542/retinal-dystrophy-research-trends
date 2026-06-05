"""Render study notes from Markdown into the site.

Turns every notes/*.md file into a styled HTML page under docs/notes/ and
builds docs/notes/index.html — a newest-first listing — so the site doubles as
a personal research archive.

Each note starts with a simple frontmatter block:

    ---
    title: Note title
    date: 2026-06-10
    tags: tag1, tag2
    lang: ko
    summary: One-line summary shown in the listing.
    ---

    Markdown body...

Usage:
    python src/build_notes.py
"""
from __future__ import annotations

import html
import re

import markdown

import config

NOTES_SRC = config.PROJECT_ROOT / "notes"
NOTES_OUT = config.PROJECT_ROOT / "docs" / "notes"

# Shared nav used on every note page and the index (sits at docs/notes/).
NAV = """  <nav class="nav">
    <div class="nav-inner">
      <a class="nav-brand" href="../index.html">🔬 IRD Research Landscape</a>
      <div class="nav-links">
        <a href="../index.html#dashboard">대시보드</a>
        <a href="../clinical-trials.html">임상시험</a>
        <a href="index.html">연구 노트</a>
        <a href="../about-cone-dystrophy.html">기초 개념</a>
        <a href="../paper/index.html">논문 번역</a>
      </div>
    </div>
  </nav>"""

FOOTER = """  <footer class="footer">
    <p><a href="index.html">← 연구 노트 목록</a> · <a href="../index.html">대시보드</a></p>
    <p>개인 연구 아카이브 · 교육·연구 목적</p>
    <p>문의 · <a href="mailto:seoyeom542@gmail.com">seoyeom542@gmail.com</a></p>
  </footer>"""

NOTE_PAGE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — 연구 노트</title>
  <meta name="description" content="{summary}" />
  <link rel="canonical" href="https://seoyeom542.github.io/retinal-dystrophy-research-trends/notes/{slug}.html" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{summary}" />
  <meta property="og:url" content="https://seoyeom542.github.io/retinal-dystrophy-research-trends/notes/{slug}.html" />
  <meta property="og:image" content="https://seoyeom542.github.io/retinal-dystrophy-research-trends/assets/keyword_wordcloud.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="stylesheet" href="../style.css" />
</head>
<body>

{nav}

  <article class="article">
    <p class="meta">연구 노트 · {date}{tag_meta}</p>
    <h1>{title}</h1>
{body}
  </article>

{footer}

</body>
</html>
"""

INDEX_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>연구 노트 — IRD Research Landscape</title>
  <meta name="description" content="유전성 망막이영양증을 공부하며 정리한 연구 노트 모음." />
  <link rel="canonical" href="https://seoyeom542.github.io/retinal-dystrophy-research-trends/notes/" />
  <meta property="og:type" content="website" />
  <meta property="og:title" content="연구 노트 — IRD Research Landscape" />
  <meta property="og:description" content="유전성 망막이영양증을 공부하며 정리한 연구 노트 모음." />
  <meta property="og:url" content="https://seoyeom542.github.io/retinal-dystrophy-research-trends/notes/" />
  <meta property="og:image" content="https://seoyeom542.github.io/retinal-dystrophy-research-trends/assets/keyword_wordcloud.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="stylesheet" href="../style.css" />
</head>
<body>

{nav}

  <header class="hero">
    <p class="subtitle">개인 연구 아카이브</p>
    <h1>연구 노트</h1>
    <p class="desc">유전성 망막이영양증을 공부하며 정리한 노트를 모아 둡니다.{count_desc}</p>
  </header>

  <main class="section">
{cards}
  </main>

{footer}

</body>
</html>
"""


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a note into its frontmatter dict and Markdown body."""
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        # Match the first fenced ---...--- block.
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if m:
            block, body = m.group(1), m.group(2)
            for line in block.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip().lower()] = value.strip()
    return meta, body


def render_note(path) -> dict:
    """Render one Markdown note to HTML; return its metadata + output slug."""
    meta, body = parse_frontmatter(path.read_text())
    slug = path.stem  # filename without .md

    md = markdown.Markdown(extensions=["extra", "tables", "fenced_code", "sane_lists"])
    body_html = md.convert(body)

    title = meta.get("title", slug)
    date = meta.get("date", "")
    lang = meta.get("lang", "ko")
    summary = meta.get("summary", "")
    tags = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    tag_meta = (" · " + " · ".join(f"#{t}" for t in tags)) if tags else ""

    page = NOTE_PAGE.format(
        lang=lang,
        title=html.escape(title),
        summary=html.escape(summary),
        slug=slug,
        date=html.escape(date),
        tag_meta=tag_meta,
        body=body_html,
        nav=NAV,
        footer=FOOTER,
    )
    NOTES_OUT.mkdir(parents=True, exist_ok=True)
    (NOTES_OUT / f"{slug}.html").write_text(page)

    return {"slug": slug, "title": title, "date": date, "summary": summary, "tags": tags}


def build_index(notes: list[dict]) -> None:
    """Build the newest-first listing page."""
    notes_sorted = sorted(notes, key=lambda n: n["date"], reverse=True)
    cards = []
    for n in notes_sorted:
        tag_html = ""
        if n["tags"]:
            chips = " ".join(f'<span class="phase-chip">#{html.escape(t)}</span>' for t in n["tags"])
            tag_html = f'<div style="margin-top:8px">{chips}</div>'
        cards.append(
            f'''      <a class="note-card" href="{n["slug"]}.html">
        <div class="note-date">{html.escape(n["date"])}</div>
        <div class="note-title">{html.escape(n["title"])}</div>
        <div class="note-summary">{html.escape(n["summary"])}</div>{tag_html}
      </a>'''
        )
    count_desc = f" 현재 {len(notes)}개의 노트가 있습니다." if notes else ""
    page = INDEX_PAGE.format(
        nav=NAV,
        footer=FOOTER,
        count_desc=count_desc,
        cards="\n".join(cards) if cards else '      <p class="trials-empty">아직 노트가 없습니다.</p>',
    )
    (NOTES_OUT / "index.html").write_text(page)


def main() -> None:
    NOTES_OUT.mkdir(parents=True, exist_ok=True)
    sources = sorted(NOTES_SRC.glob("*.md"))
    notes = [render_note(p) for p in sources]
    for n in notes:
        print(f"  wrote docs/notes/{n['slug']}.html")
    build_index(notes)
    print(f"  wrote docs/notes/index.html ({len(notes)} notes)")


if __name__ == "__main__":
    main()

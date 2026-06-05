# Inherited Retinal Dystrophy Research Landscape

**유전성 망막이영양증 연구 동향 문헌 분석**

PubMed 메타데이터로 추체이영양증(cone dystrophy)을 포함한 유전성 망막이영양증
(inherited retinal dystrophy) 분야의 연구 동향을 수집·분석·시각화하고, 그 결과를
일반인과 연구자 모두가 볼 수 있는 웹 페이지로 제공하는 프로젝트입니다.

> A literature analysis of inherited retinal dystrophy research, built on PubMed
> metadata and published as an interactive GitHub Pages dashboard.

---

## 분석 주제

- 연도별 논문 발행 수 추이
- 가장 많이 언급된 유전자 Top 10 (ABCA4, RPGR, GUCA1A, KCNV2 등)
- 치료 방법별 연구 비중 (유전자 치료 · 유전자 편집 · 줄기세포 · 광유전학 등)
- 키워드 동시 출현(co-occurrence) 분석
- 주요 저널 · 저자 분포

---

## 프로젝트 구조

```
retinal-dystrophy-research-trends/
├── src/
│   ├── config.py          # 검색어 · 경로 · 유전자/치료법 사전 (모든 단계가 공유)
│   └── fetch_pubmed.py     # [1단계] PubMed 수집 → data/raw/pubmed_records.json
├── data/
│   ├── raw/                # 수집한 원본 메타데이터 (gitignore 처리)
│   └── processed/          # 분석용 정제 데이터
├── notebooks/             # 탐색적 분석 노트북
├── docs/                  # GitHub Pages 정적 사이트
├── requirements.txt
└── .env.example           # NCBI 인증 정보 템플릿
```

---

## 개발 로드맵

| 단계 | 내용 | 상태 |
|------|------|------|
| 1단계 | PubMed API 데이터 수집 (`src/fetch_pubmed.py`) | ✅ 완료 |
| 2단계 | Pandas 기반 데이터 분석 (`src/analyze.py`) | ✅ 완료 |
| 3단계 | Plotly 인터랙티브 시각화 (`src/visualize.py`) | ✅ 완료 |
| 4단계 | GitHub Pages 대시보드 (`docs/`) | ✅ 완료 |

---

## 시작하기

### 1. 환경 설정

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. NCBI 인증 정보 설정

NCBI Entrez는 요청마다 연락용 이메일을 요구합니다. API 키는 선택이지만 요청
한도를 초당 3회 → 10회로 높여줍니다 ([발급 안내](https://www.ncbi.nlm.nih.gov/account/)).

```bash
cp .env.example .env
# .env 파일을 열어 NCBI_EMAIL (필수), NCBI_API_KEY (선택)를 입력
```

### 3. 데이터 수집 실행

```bash
# 모든 검색어로 수집 (기본 캡: 검색어당 2000건)
python src/fetch_pubmed.py

# 빠른 테스트: 검색어당 30건만
python src/fetch_pubmed.py --max 30

# 특정 검색어만
python src/fetch_pubmed.py --query cone_dystrophy
```

결과는 `data/raw/pubmed_records.json`에 저장됩니다. PMID 기준으로 중복이
제거되며, 한 논문이 여러 검색어에 걸리면 `query_labels`에 모두 기록됩니다.

수집되는 필드: `pmid`, `title`, `year`, `journal`, `authors`, `abstract`,
`keywords`(MeSH + 저자 키워드), `query_labels`.

---

### 4. 전체 파이프라인 실행 & 웹 페이지

```bash
python src/fetch_pubmed.py      # 1단계: 수집  -> data/raw/
python src/analyze.py           # 2단계: 분석  -> data/processed/
python src/visualize.py         # 3단계: 차트  -> docs/charts/, docs/assets/

# 4단계: 로컬 미리보기
python -m http.server 8000 --directory docs
# 브라우저에서 http://localhost:8000 열기
```

### GitHub Pages 배포

1. 이 저장소를 GitHub에 push 합니다.
2. 저장소 **Settings → Pages** 로 이동합니다.
3. **Source**를 `Deploy from a branch`, **Branch**를 `main` / **`/docs`** 폴더로 지정합니다.
4. 잠시 후 `https://<사용자명>.github.io/retinal-dystrophy-research-trends/` 에서 공개됩니다.

`docs/` 안에 정적 사이트가 모두 들어 있습니다.

```
docs/
├── index.html                  # 대시보드 (히어로 + 인터랙티브 차트 5종)
├── clinical-trials.html         # 임상시험 현황 (ClinicalTrials.gov, 상태별 필터)
├── about-cone-dystrophy.html    # 추체이영양증 기초 개념 설명
├── paper/index.html             # 논문 한국어 번역 (CC BY 표기)
├── paper/source/                # 원문 PDF를 두는 곳
├── charts/                      # Plotly 인터랙티브 차트 HTML
├── assets/                      # 워드클라우드 등 이미지
└── style.css
```

### 임상시험 데이터 갱신

```bash
python src/fetch_trials.py        # ClinicalTrials.gov API v2 -> data/processed/clinical_trials.json
python src/build_trials_page.py   # 데이터를 임베드한 docs/clinical-trials.html 생성
```

IRD 관련 8개 질환 조건과 유전자치료 중재(intervention)를 교차 검색해 임상시험을
수집하고, 상태별 필터링이 가능한 정적 페이지로 빌드합니다.

## 데이터 출처 및 라이선스

- **메타데이터**: [PubMed](https://pubmed.ncbi.nlm.nih.gov/) / NCBI Entrez
  E-utilities. [NCBI 이용 약관](https://www.ncbi.nlm.nih.gov/home/about/policies/)을
  따릅니다.
- 향후 게시될 논문 번역본은 각 논문의 라이선스를 개별 확인하여 게시합니다.
  예: Gill JS, et al. *Br J Ophthalmol* 2019;103:711–720
  (doi:10.1136/bjophthalmol-2018-313278) — **CC BY 4.0**, 출처 표기 후 번역·재배포 허용.

# -*- coding: utf-8 -*-
"""Submission dashboard for conference/journal deadline tracking.

Run locally:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "weights.json"

KST = ZoneInfo("Asia/Seoul")
TODAY = datetime.now(KST).date()
STALE_DAYS = 60

KRW_RATES = {
    "KRW": 1,
    "USD": 1350,
    "EUR": 1470,
    "GBP": 1720,
    "JPY": 9.2,
    "AUD": 890,
    "CAD": 990,
    "CHF": 1510,
    "SGD": 1000,
}

st.set_page_config(page_title="Submission Dashboard", page_icon="📚", layout="wide")


def apply_theme(mode: str) -> None:
    dark = mode == "다크"
    bg = "#0b1120" if dark else "#f7f9fc"
    panel = "#111827" if dark else "#ffffff"
    panel_2 = "#172033" if dark else "#eef4ff"
    text = "#e5e7eb" if dark else "#111827"
    muted = "#9ca3af" if dark else "#64748b"
    border = "#334155" if dark else "#d8e1ef"
    accent = "#60a5fa" if dark else "#2563eb"
    accent_2 = "#22c55e" if dark else "#15803d"
    danger = "#f87171" if dark else "#b91c1c"
    shadow = "none" if dark else "0 10px 22px rgba(15, 23, 42, 0.06)"

    st.markdown(
        f"""
        <style>
        :root {{
            --app-bg: {bg};
            --panel: {panel};
            --panel-2: {panel_2};
            --text: {text};
            --muted: {muted};
            --border: {border};
            --accent: {accent};
            --accent-2: {accent_2};
            --danger: {danger};
            --shadow: {shadow};
        }}
        .stApp {{ background: var(--app-bg); color: var(--text); }}
        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }}
        [data-testid="stSidebar"] {{
            background: var(--panel);
            border-right: 1px solid var(--border);
        }}
        h1, h2, h3, h4, h5, h6, p, label, span, div {{
            color: var(--text);
        }}
        h1 {{ font-size: 2rem; line-height: 1.2; margin-bottom: 0.2rem; }}
        h2, h3 {{ letter-spacing: 0; }}
        .muted {{ color: var(--muted); }}
        .hero {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: var(--shadow);
            margin-bottom: 18px;
        }}
        .hero-title {{
            font-size: 1.95rem;
            font-weight: 750;
            line-height: 1.2;
            margin-bottom: 6px;
        }}
        .hero-copy {{
            color: var(--muted);
            font-size: 0.98rem;
        }}
        .pill-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
        .pill {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border: 1px solid var(--border);
            background: var(--panel-2);
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 0.82rem;
            color: var(--text);
            white-space: nowrap;
        }}
        [data-testid="stMetric"] {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 13px 14px;
            box-shadow: var(--shadow);
        }}
        [data-testid="stMetricLabel"] p {{ color: var(--muted); }}
        [data-testid="stMetricValue"] div {{ color: var(--text); font-size: 1.55rem; }}
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            margin-bottom: 12px;
        }}
        .stTabs [data-baseweb="tab"] {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 9px;
            padding: 9px 14px;
            min-height: 44px;
        }}
        .stTabs [aria-selected="true"] {{
            background: var(--panel-2);
            border-color: var(--accent);
        }}
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
            background: var(--panel-2);
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
            min-height: 38px;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
            border-color: var(--accent);
            color: var(--accent);
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            background: var(--panel);
        }}
        [data-testid="stExpander"] {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
        }}
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin: 10px 0 16px;
        }}
        .detail-box {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 13px 14px;
        }}
        .detail-label {{
            color: var(--muted);
            font-size: 0.78rem;
            margin-bottom: 5px;
        }}
        .detail-value {{
            font-weight: 650;
            line-height: 1.35;
        }}
        .small-note {{
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.5;
        }}
        @media (max-width: 900px) {{
            .detail-grid {{ grid-template-columns: 1fr; }}
            .hero-title {{ font-size: 1.55rem; }}
            .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def clean_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


@st.cache_data(ttl=300)
def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / name, dtype=str, encoding="utf-8-sig").fillna("")
    df.columns = [c.strip() for c in df.columns]
    return df


def load_weights() -> dict:
    default = {
        "fit_score": 0.30,
        "strategic_value": 0.25,
        "submission_probability": 0.20,
        "publication_value": 0.15,
        "effort_required": -0.05,
        "cost_burden": -0.05,
    }
    try:
        return {**default, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    except Exception:
        return default


def to_date(value: str):
    try:
        return datetime.strptime(clean_text(value), "%Y-%m-%d").date()
    except Exception:
        return None


def dday(value: str):
    d = to_date(value)
    return None if d is None else (d - TODAY).days


def dday_label(value: str) -> str:
    n = dday(value)
    if n is None:
        return "상시/미정"
    if n < 0:
        return f"마감 D+{-n}"
    if n == 0:
        return "오늘 마감"
    return f"D-{n}"


def urgency(value: str) -> str:
    n = dday(value)
    if n is None:
        return "상시/미정"
    if n < 0:
        return "마감 지남"
    if n <= 7:
        return "7일 이내"
    if n <= 30:
        return "30일 이내"
    if n <= 60:
        return "60일 이내"
    return "여유"


def is_stale(value: str) -> bool:
    d = to_date(value)
    return d is not None and (TODAY - d).days > STALE_DAYS


def numeric_amount(value: str):
    match = re.search(r"[\d,.]+", clean_text(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def to_krw(amount: str, currency: str):
    value = numeric_amount(amount)
    rate = KRW_RATES.get(clean_text(currency).upper())
    if value is None or rate is None:
        return None
    return int(round(value * rate / 1000) * 1000)


def fmt_money(amount: str, currency: str) -> str:
    amount = clean_text(amount)
    currency = clean_text(currency).upper()
    if not amount:
        return "금액 미공개"
    krw = to_krw(amount, currency)
    if currency == "KRW":
        return f"{int(numeric_amount(amount) or 0):,}원"
    if krw is None:
        return f"{amount} {currency}"
    return f"{krw:,}원({amount} {currency})"


def first_nonempty(*values: str) -> str:
    for value in values:
        value = clean_text(value)
        if value:
            return value
    return ""


def is_verified(value: str) -> bool:
    return clean_text(value).startswith("verified")


def scope_label(scope: str) -> str:
    return {
        "core": "핵심 후보",
        "secondary": "보조 후보",
        "project_specific_only": "특정 주제 후보",
    }.get(clean_text(scope), clean_text(scope) or "미분류")


def status_label(status: str) -> str:
    return {
        "open": "접수중",
        "upcoming": "예정",
        "rolling": "상시",
        "closed": "마감",
        "watch": "관찰",
    }.get(clean_text(status), clean_text(status) or "미정")


def metric_summary(row: pd.Series) -> str:
    bits = []
    for label, col in [
        ("SCI", "sci_status"),
        ("SCIE", "scie_status"),
        ("SSCI", "ssci_status"),
        ("AHCI", "ahci_status"),
    ]:
        if clean_text(row.get(col)):
            bits.append(label)
    if clean_text(row.get("scopus_status")):
        bits.append(f"Scopus {clean_text(row.get('scopus_status'))}")
    if clean_text(row.get("core_ranking")):
        bits.append(f"CORE {clean_text(row.get('core_ranking'))}")
    if clean_text(row.get("impact_factor")):
        bits.append(f"IF {clean_text(row.get('impact_factor'))}")
    if clean_text(row.get("cite_score")):
        bits.append(f"CiteScore {clean_text(row.get('cite_score'))}")
    if clean_text(row.get("h5_index")):
        bits.append(f"h5 {clean_text(row.get('h5_index'))}")
    if clean_text(row.get("acceptance_rate")):
        bits.append(f"acceptance {clean_text(row.get('acceptance_rate'))}")
    return " · ".join(bits)


def level_label(row: pd.Series) -> str:
    summary = clean_text(row.get("metric_summary"))
    if summary:
        return summary
    scope = clean_text(row.get("priority_scope"))
    venue_type = clean_text(row.get("venue_type"))
    if scope == "core":
        return "핵심 후보 · 정량 지표 보강 필요"
    if venue_type == "journal":
        return "저널 지표 확인 필요"
    return "학회 지표 확인 필요"


def tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9가-힣#.-]{2,}", clean_text(text))]


def keyword_score(row: pd.Series, query: str) -> tuple[int, str]:
    qs = tokens(query)
    if not qs:
        return 0, ""
    haystack = " ".join(
        clean_text(row.get(col))
        for col in [
            "acronym",
            "venue_name",
            "venue_type",
            "field",
            "primary_relevance",
            "secondary_relevance",
            "domain_fit_notes",
            "typical_submission_types",
            "track_name",
            "submission_type",
            "fit_rationale_public_safe",
            "notes",
        ]
    ).lower()
    matched = []
    score = 0
    for q in qs:
        if q in haystack:
            matched.append(q)
            score += 3 if q in clean_text(row.get("primary_relevance")).lower() else 1
    return score, ", ".join(sorted(set(matched)))


def calc_priority(row: pd.Series, weights: dict) -> float:
    score_cols = [
        "fit_score",
        "submission_probability",
        "strategic_value",
        "publication_value",
        "effort_required",
        "cost_burden",
    ]
    vals = {}
    for col in score_cols:
        try:
            vals[col] = float(clean_text(row.get(col)) or 0)
        except ValueError:
            vals[col] = 0
    base = (
        vals["fit_score"] * weights["fit_score"]
        + vals["strategic_value"] * weights["strategic_value"]
        + vals["submission_probability"] * weights["submission_probability"]
        + vals["publication_value"] * weights["publication_value"]
        + vals["effort_required"] * weights["effort_required"]
        + vals["cost_burden"] * weights["cost_burden"]
    )
    n = dday(clean_text(row.get("paper_deadline")))
    if n is not None and 0 <= n <= 45:
        base += 0.35
    if clean_text(row.get("status")) == "rolling":
        base += 0.15
    if clean_text(row.get("priority_scope")) == "core":
        base += 0.25
    return round(base, 2)


def build_database(
    venues: pd.DataFrame,
    opps: pd.DataFrame,
    fees: pd.DataFrame,
    metrics: pd.DataFrame,
    fits: pd.DataFrame,
) -> pd.DataFrame:
    verified_metrics = metrics[metrics["verification_status"].map(is_verified)].copy()
    verified_metrics["_year"] = pd.to_numeric(verified_metrics["metric_year"], errors="coerce").fillna(0)
    latest_metric = verified_metrics.sort_values("_year").groupby("venue_id", as_index=False).tail(1)
    latest_metric["metric_summary"] = latest_metric.apply(metric_summary, axis=1)

    fees = fees.copy()
    fees["_fee_priority"] = fees["verification_status"].map(lambda v: 0 if is_verified(v) else 1)
    fees["_amount_present"] = fees["amount"].map(lambda v: 0 if clean_text(v) else 1)
    fee_one = (
        fees.sort_values(["_amount_present", "_fee_priority", "last_checked_at"], ascending=[True, True, False])
        .groupby(["opportunity_id", "venue_id"], dropna=False, as_index=False)
        .head(1)
    )

    weights = load_weights()
    fit_one = fits.copy()
    fit_one["_fit"] = pd.to_numeric(fit_one.get("fit_score", 0), errors="coerce").fillna(0)
    fit_one = fit_one.sort_values("_fit", ascending=False).groupby("opportunity_id", as_index=False).head(1)

    db = (
        opps.merge(
            venues[
                [
                    "venue_id",
                    "venue_name",
                    "acronym",
                    "venue_type",
                    "field",
                    "publisher",
                    "society",
                    "official_homepage_url",
                    "priority_scope",
                    "primary_relevance",
                    "secondary_relevance",
                    "domain_fit_notes",
                    "typical_submission_types",
                    "verification_status",
                ]
            ].rename(columns={"verification_status": "venue_verification_status"}),
            on="venue_id",
            how="left",
        )
        .merge(
            latest_metric[
                [
                    "venue_id",
                    "metric_year",
                    "metric_summary",
                    "metric_source_url",
                    "metric_source_type",
                    "verification_status",
                ]
            ].rename(columns={"verification_status": "metric_verification_status"}),
            on="venue_id",
            how="left",
        )
        .merge(
            fee_one[
                [
                    "opportunity_id",
                    "venue_id",
                    "fee_type",
                    "category",
                    "amount",
                    "currency",
                    "fee_deadline",
                    "fee_source_url",
                    "verification_status",
                    "notes",
                ]
            ].rename(columns={"verification_status": "fee_verification_status", "notes": "fee_notes"}),
            on=["opportunity_id", "venue_id"],
            how="left",
        )
        .merge(
            fit_one[
                [
                    "opportunity_id",
                    "project_id",
                    "fit_score",
                    "fit_rationale_public_safe",
                    "expected_difficulty",
                    "submission_probability",
                    "strategic_value",
                    "publication_value",
                    "effort_required",
                    "cost_burden",
                    "risk_tags",
                    "next_action_public_safe",
                    "internal_deadline",
                ]
            ],
            on="opportunity_id",
            how="left",
        )
        .fillna("")
    )

    db["verified_public"] = db["verification_status"].map(is_verified) & db["venue_verification_status"].map(is_verified)
    db["deadline_label"] = db["paper_deadline"].map(dday_label)
    db["urgency"] = db["paper_deadline"].map(urgency)
    db["status_label"] = db["status"].map(status_label)
    db["scope_label"] = db["priority_scope"].map(scope_label)
    db["level"] = db.apply(level_label, axis=1)
    db["cost"] = db.apply(lambda r: fmt_money(r.get("amount"), r.get("currency")), axis=1)
    db["cost_basis"] = db.apply(
        lambda r: "공식 금액 확인" if is_verified(r.get("fee_verification_status")) and clean_text(r.get("amount")) else "올해/작년 등록비 확인 필요",
        axis=1,
    )
    db["deadline_kst"] = db.apply(
        lambda r: " ".join(
            part
            for part in [
                clean_text(r.get("paper_deadline")),
                clean_text(r.get("deadline_time")),
                clean_text(r.get("deadline_timezone")),
            ]
            if part
        )
        or "상시/미정",
        axis=1,
    )
    db["priority_score"] = db.apply(lambda r: calc_priority(r, weights), axis=1)
    return db


def style_urgency(df: pd.DataFrame, col: str = "마감감") -> pd.io.formats.style.Styler:
    colors = {
        "7일 이내": "background-color:#7f1d1d;color:#fee2e2",
        "30일 이내": "background-color:#78350f;color:#ffedd5",
        "60일 이내": "background-color:#713f12;color:#fef3c7",
        "마감 지남": "color:#94a3b8",
    }

    def _row(row):
        return [colors.get(row.get(col, ""), "")] * len(row)

    return df.style.apply(_row, axis=1)


def link_col(label: str) -> st.column_config.LinkColumn:
    return st.column_config.LinkColumn(label, display_text=label)


def render_detail_box(label: str, value: str) -> str:
    value = clean_text(value) or "-"
    return f"""
    <div class="detail-box">
      <div class="detail-label">{label}</div>
      <div class="detail-value">{value}</div>
    </div>
    """


def public_view(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["verified_public"]].copy()


with st.sidebar:
    theme_mode = st.radio("화면 모드", ["다크", "라이트"], horizontal=True)
    st.caption("공개 화면은 검증된 학회/저널과 제출 기회만 보여줍니다.")
    show_admin = st.toggle("관리자 도구 표시", value=False)

apply_theme(theme_mode)

venues = load("venues.csv")
opps = load("opportunities.csv")
fees = load("fees.csv")
metrics = load("metrics.csv")
sources = load("sources.csv")
projects = load("projects.csv")
fits = load("project_opportunity_fit.csv")
watch = load("watchlist.csv")

db = build_database(venues, opps, fees, metrics, fits)
base = public_view(db)

st.markdown(
    f"""
    <div class="hero">
      <div class="hero-title">학회·저널 제출 후보 데이터베이스</div>
      <div class="hero-copy">
        같은 후보 목록을 일정, 수준, 비용, 프로젝트 적합도 관점으로 탐색합니다.
        CFP는 Call for Papers의 약자로, 논문·발표 모집요강을 뜻합니다.
      </div>
      <div class="pill-row">
        <span class="pill">오늘 {TODAY.isoformat()} KST</span>
        <span class="pill">공개 뷰: 검증 완료 {len(base)}건</span>
        <span class="pill">내부 추적 전체 {len(db)}건</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### 탐색 필터")
    q = st.text_input("키워드", placeholder="AI UX, mobile banking, accessibility")
    status_options = sorted(base["status_label"].dropna().unique())
    status_sel = st.multiselect("상태", status_options, default=[s for s in ["접수중", "예정", "상시"] if s in status_options])
    field_sel = st.multiselect("분야", sorted(v for v in base["field"].unique() if v))
    type_sel = st.multiselect("유형", sorted(v for v in base["venue_type"].unique() if v))
    scope_sel = st.multiselect("우선순위", sorted(v for v in base["scope_label"].unique() if v))
    only_with_deadline = st.checkbox("마감일 있는 항목만", value=False)
    hide_closed = st.checkbox("마감 지난 항목 숨기기", value=True)

view = base.copy()
if q:
    scores = view.apply(lambda r: keyword_score(r, q), axis=1)
    view["키워드 점수"] = [s[0] for s in scores]
    view["매칭 키워드"] = [s[1] for s in scores]
    view = view[view["키워드 점수"] > 0]
else:
    view["키워드 점수"] = 0
    view["매칭 키워드"] = ""
if status_sel:
    view = view[view["status_label"].isin(status_sel)]
if field_sel:
    view = view[view["field"].isin(field_sel)]
if type_sel:
    view = view[view["venue_type"].isin(type_sel)]
if scope_sel:
    view = view[view["scope_label"].isin(scope_sel)]
if only_with_deadline:
    view = view[view["paper_deadline"].map(lambda s: to_date(s) is not None)]
if hide_closed:
    view = view[view["urgency"] != "마감 지남"]

metric_cols = st.columns(4)
metric_cols[0].metric("탐색 후보", len(view))
metric_cols[1].metric("30일 이내", int(view["urgency"].isin(["7일 이내", "30일 이내"]).sum()))
metric_cols[2].metric("비용 확인", int((view["cost_basis"] == "공식 금액 확인").sum()))
metric_cols[3].metric("상시/미정", int((view["urgency"] == "상시/미정").sum()))

tabs = st.tabs(["🗂 후보 DB", "🧭 탐색 보드", "📅 일정", "💰 비용", "🔎 상세", "🛠 관리"])

table_cols = [
    "priority_score",
    "acronym",
    "track_name",
    "submission_type",
    "deadline_kst",
    "deadline_label",
    "urgency",
    "level",
    "cost",
    "cost_basis",
    "scope_label",
    "status_label",
    "official_cfp_url",
]
display_names = {
    "priority_score": "추천 점수",
    "acronym": "이름",
    "track_name": "트랙",
    "submission_type": "제출 유형",
    "deadline_kst": "마감",
    "deadline_label": "D-day",
    "urgency": "긴급도",
    "level": "학회/저널 수준",
    "cost": "등록비/APC",
    "cost_basis": "비용 근거",
    "scope_label": "분류",
    "status_label": "상태",
    "official_cfp_url": "모집요강",
}

with tabs[0]:
    st.subheader("후보 데이터베이스")
    st.caption("검증 상태는 사용자 화면에서 숨기고, 검증된 항목만 기본 목록에 노출합니다.")
    table = view.sort_values(["priority_score", "paper_deadline"], ascending=[False, True])[table_cols].rename(columns=display_names)
    st.dataframe(
        style_urgency(table, "긴급도"),
        use_container_width=True,
        hide_index=True,
        column_config={"모집요강": link_col("모집요강")},
    )

with tabs[1]:
    st.subheader("유기적 탐색 보드")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 지금 제출하기 좋은 후보")
        now = view[view["status"].isin(["open", "upcoming", "rolling"])].sort_values("priority_score", ascending=False).head(8)
        st.dataframe(
            now[["acronym", "track_name", "deadline_label", "level", "cost", "official_cfp_url"]].rename(
                columns={
                    "acronym": "이름",
                    "track_name": "트랙",
                    "deadline_label": "D-day",
                    "level": "수준",
                    "cost": "비용",
                    "official_cfp_url": "모집요강",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"모집요강": link_col("모집요강")},
        )
    with c2:
        st.markdown("#### 비용 확인이 필요한 후보")
        cost_unknown = view[view["cost_basis"] != "공식 금액 확인"].sort_values(["priority_score"], ascending=False).head(8)
        st.dataframe(
            cost_unknown[["acronym", "track_name", "cost_basis", "fee_source_url", "official_homepage_url"]].rename(
                columns={
                    "acronym": "이름",
                    "track_name": "트랙",
                    "cost_basis": "상태",
                    "fee_source_url": "등록비 페이지",
                    "official_homepage_url": "홈페이지",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"등록비 페이지": link_col("등록비 페이지"), "홈페이지": link_col("홈페이지")},
        )
    with c3:
        st.markdown("#### 지표 보강이 필요한 후보")
        metric_unknown = view[view["metric_summary"].map(lambda v: not clean_text(v))].sort_values("priority_score", ascending=False).head(8)
        st.dataframe(
            metric_unknown[["acronym", "venue_type", "scope_label", "official_homepage_url"]].rename(
                columns={"acronym": "이름", "venue_type": "유형", "scope_label": "분류", "official_homepage_url": "홈페이지"}
            ),
            use_container_width=True,
            hide_index=True,
            column_config={"홈페이지": link_col("홈페이지")},
        )

    st.markdown("#### 프로젝트 적합도")
    fit_cols = [
        "project_id",
        "acronym",
        "track_name",
        "fit_score",
        "submission_probability",
        "strategic_value",
        "publication_value",
        "expected_difficulty",
        "next_action_public_safe",
    ]
    fit_view = view[view["project_id"].map(lambda v: bool(clean_text(v)))].sort_values("priority_score", ascending=False)
    if len(fit_view):
        st.dataframe(
            fit_view[fit_cols].rename(
                columns={
                    "project_id": "프로젝트",
                    "acronym": "이름",
                    "track_name": "트랙",
                    "fit_score": "적합도",
                    "submission_probability": "제출 가능성",
                    "strategic_value": "전략성",
                    "publication_value": "출판 가치",
                    "expected_difficulty": "난이도",
                    "next_action_public_safe": "다음 행동",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("현재 필터 조건에 맞는 프로젝트 적합도 데이터가 없습니다.")

with tabs[2]:
    st.subheader("마감 일정")
    ics_path = ROOT / "public" / "submission_deadlines.ics"
    try:
        sub_url = json.loads((ROOT / "config" / "calendar.json").read_text(encoding="utf-8")).get("ics_public_url", "")
    except Exception:
        sub_url = ""
    left, right = st.columns(2)
    if sub_url:
        webcal = sub_url.replace("https://", "webcal://")
        gcal = "https://calendar.google.com/calendar/r?cid=" + quote(webcal, safe="")
        outlook = "https://outlook.live.com/calendar/0/addfromweb?url=" + quote(sub_url, safe="") + "&name=" + quote("제출 마감 캘린더")
        left.link_button("Google Calendar 구독", gcal, use_container_width=True)
        left.link_button("Outlook 구독", outlook, use_container_width=True)
        with left.expander("수동 구독 URL"):
            st.code(sub_url, language=None)
    else:
        left.info("config/calendar.json의 ics_public_url을 채우면 캘린더 구독 버튼이 표시됩니다.")
    if ics_path.exists():
        mtime = datetime.fromtimestamp(ics_path.stat().st_mtime, KST).strftime("%Y-%m-%d %H:%M KST")
        right.caption(f"ICS 마지막 생성: {mtime}")
        right.download_button("ICS 다운로드", ics_path.read_bytes(), "submission_deadlines.ics", "text/calendar")

    events = []
    for _, r in view.iterrows():
        for col, label in [
            ("abstract_deadline", "초록"),
            ("paper_deadline", "논문"),
            ("notification_date", "결과 발표"),
            ("camera_ready_deadline", "최종본"),
            ("conference_start", "행사 시작"),
        ]:
            if clean_text(r.get(col)):
                events.append(
                    {
                        "date": r[col],
                        "event": label,
                        "venue": r["acronym"],
                        "track": r["track_name"],
                        "status": r["status_label"],
                        "timezone": r["deadline_timezone"],
                        "D-day": dday_label(r[col]),
                        "urgency": urgency(r[col]),
                        "모집요강": r["official_cfp_url"],
                    }
                )
    cal = pd.DataFrame(events)
    if cal.empty:
        st.info("표시할 일정이 없습니다.")
    else:
        st.dataframe(
            style_urgency(cal.sort_values("date").rename(columns={"date": "날짜", "event": "일정", "venue": "이름", "track": "트랙", "status": "상태", "timezone": "시간대", "urgency": "긴급도"}), "긴급도"),
            use_container_width=True,
            hide_index=True,
            column_config={"모집요강": link_col("모집요강")},
        )

with tabs[3]:
    st.subheader("비용")
    st.caption("금액이 없으면 올해 등록 페이지나 작년 등록 페이지를 확인해야 하는 후보로 분리합니다.")
    cost_cols = [
        "acronym",
        "track_name",
        "fee_type",
        "category",
        "cost",
        "cost_basis",
        "fee_deadline",
        "fee_source_url",
        "official_homepage_url",
    ]
    cost_view = view.sort_values(["cost_basis", "priority_score"], ascending=[True, False])[cost_cols].rename(
        columns={
            "acronym": "이름",
            "track_name": "트랙",
            "fee_type": "비용 유형",
            "category": "구분",
            "cost": "금액",
            "cost_basis": "근거",
            "fee_deadline": "비용 마감",
            "fee_source_url": "등록비 페이지",
            "official_homepage_url": "홈페이지",
        }
    )
    st.dataframe(
        cost_view,
        use_container_width=True,
        hide_index=True,
        column_config={"등록비 페이지": link_col("등록비 페이지"), "홈페이지": link_col("홈페이지")},
    )

with tabs[4]:
    st.subheader("아이템 상세")
    if view.empty:
        st.info("현재 필터 조건에 맞는 후보가 없습니다.")
    else:
        labels = {
            f"{r.acronym} · {r.track_name or r.venue_name} · {r.deadline_label}": r.opportunity_id
            for r in view.sort_values("priority_score", ascending=False).itertuples()
        }
        selected_label = st.selectbox("후보 선택", list(labels.keys()))
        item = db[db["opportunity_id"] == labels[selected_label]].iloc[0]

        st.markdown(f"### {item['acronym']} · {item['track_name']}")
        st.markdown(
            f"""
            <div class="detail-grid">
                {render_detail_box("제출 마감", item["deadline_kst"] + " · " + item["deadline_label"])}
                {render_detail_box("학회/저널 수준", item["level"])}
                {render_detail_box("등록비/APC", item["cost"] + " · " + item["cost_basis"])}
                {render_detail_box("제출 유형", item["submission_type"])}
                {render_detail_box("분야", item["field"])}
                {render_detail_box("우선순위", item["scope_label"])}
            </div>
            """,
            unsafe_allow_html=True,
        )
        d1, d2, d3 = st.columns(3)
        d1.link_button("모집요강 열기", item["official_cfp_url"] or item["official_homepage_url"], use_container_width=True)
        if clean_text(item["submission_system_url"]):
            d2.link_button("제출 시스템", item["submission_system_url"], use_container_width=True)
        if clean_text(item["fee_source_url"]):
            d3.link_button("등록비 페이지", item["fee_source_url"], use_container_width=True)

        info_tabs = st.tabs(["개요", "일정/형식", "비용/수준", "프로젝트 적합도"])
        with info_tabs[0]:
            st.write(item["venue_name"])
            st.markdown(f"<div class='small-note'>{clean_text(item['domain_fit_notes']) or clean_text(item['notes'])}</div>", unsafe_allow_html=True)
        with info_tabs[1]:
            schedule = pd.DataFrame(
                [
                    {"항목": "초록", "날짜": item["abstract_deadline"]},
                    {"항목": "논문", "날짜": item["paper_deadline"]},
                    {"항목": "결과 발표", "날짜": item["notification_date"]},
                    {"항목": "최종본", "날짜": item["camera_ready_deadline"]},
                    {"항목": "행사", "날짜": f"{item['conference_start']} - {item['conference_end']}"},
                ]
            )
            st.dataframe(schedule, use_container_width=True, hide_index=True)
            st.write(f"형식: {first_nonempty(item['format'], item['page_limit'], item['word_limit'], item['typical_submission_types']) or '-'}")
        with info_tabs[2]:
            st.write(f"수준: {item['level']}")
            st.write(f"지표 기준연도: {clean_text(item['metric_year']) or '-'}")
            st.write(f"비용: {item['cost']}")
            st.write(f"비용 확인 상태: {item['cost_basis']}")
        with info_tabs[3]:
            if clean_text(item["project_id"]):
                st.write(f"프로젝트: {item['project_id']}")
                st.write(f"적합도: {item['fit_score']} / 제출 가능성: {item['submission_probability']} / 전략성: {item['strategic_value']}")
                st.write(f"판단 근거: {item['fit_rationale_public_safe']}")
                st.write(f"다음 행동: {item['next_action_public_safe']}")
            else:
                st.info("아직 연결된 프로젝트 적합도 평가가 없습니다.")

with tabs[5]:
    st.subheader("관리")
    if not show_admin:
        st.info("사이드바에서 관리자 도구를 켜면 검증 상태, 원본 테이블 점검, AI 제안 검토를 볼 수 있습니다.")
    else:
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("미검증 제출 기회", int((~opps["verification_status"].map(is_verified)).sum()))
        a2.metric("미검증 학회/저널", int((~venues["verification_status"].map(is_verified)).sum()))
        a3.metric("미확인 비용", int((fees["amount"].map(lambda v: not clean_text(v))).sum()))
        a4.metric("미확인 지표", int((metrics["verification_status"].map(lambda v: not is_verified(v))).sum()))

        st.markdown("#### 공개 화면에서 제외된 제출 기회")
        hidden = db[~db["verified_public"]].copy()
        st.dataframe(
            hidden[
                [
                    "opportunity_id",
                    "acronym",
                    "track_name",
                    "verification_status",
                    "venue_verification_status",
                    "official_cfp_url",
                    "notes",
                ]
            ],
            use_container_width=True,
            hide_index=True,
            column_config={"official_cfp_url": link_col("모집요강")},
        )

        st.markdown("#### 오래된 확인 날짜")
        stale_frames = []
        for name, df in [
            ("opportunities", opps),
            ("venues", venues),
            ("fees", fees),
            ("metrics", metrics),
            ("watchlist", watch),
        ]:
            if "last_checked_at" in df.columns:
                stale = df[df["last_checked_at"].map(is_stale)].copy()
                if len(stale):
                    stale.insert(0, "table", name)
                    id_cols = [c for c in stale.columns if c.endswith("_id")]
                    stale_frames.append(stale[["table"] + id_cols[:1] + ["last_checked_at", "verification_status"]])
        if stale_frames:
            st.dataframe(pd.concat(stale_frames), use_container_width=True, hide_index=True)
        else:
            st.success("오래된 확인 날짜가 없습니다.")

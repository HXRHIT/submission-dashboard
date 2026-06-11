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

st.set_page_config(page_title="Submission Dashboard", page_icon="📌", layout="wide")


def apply_theme(mode: str) -> None:
    if mode == "시스템 기본":
        return
    dark = mode == "다크"
    bg = "#0f172a" if dark else "#f8fafc"
    panel = "#111827" if dark else "#ffffff"
    text = "#e5e7eb" if dark else "#0f172a"
    muted = "#94a3b8" if dark else "#64748b"
    border = "#334155" if dark else "#dbe3ef"
    accent = "#38bdf8" if dark else "#2563eb"
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {bg}; color: {text}; }}
        [data-testid="stSidebar"] {{ background: {panel}; }}
        h1, h2, h3, h4, h5, h6, p, label, span, div {{ color: {text}; }}
        [data-testid="stMetric"] {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 8px;
            padding: 12px;
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
        .stTabs [data-baseweb="tab"] {{
            border-radius: 8px 8px 0 0;
            color: {muted};
        }}
        .stTabs [aria-selected="true"] {{
            color: {accent};
            border-bottom-color: {accent};
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid {border};
            border-radius: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


with st.sidebar:
    theme_mode = st.radio("화면 모드", ["다크", "라이트", "시스템 기본"], horizontal=True)
    show_admin = st.toggle("관리자 도구 표시", value=False)
    st.caption("기본 화면에는 의사결정에 필요한 항목만 표시합니다.")

apply_theme(theme_mode)

LINK_COLS = {
    "official_cfp_url": st.column_config.LinkColumn("CFP", display_text="CFP"),
    "deadline_source_url": st.column_config.LinkColumn("마감 출처", display_text="출처"),
    "submission_system_url": st.column_config.LinkColumn("제출", display_text="제출"),
    "template_url": st.column_config.LinkColumn("템플릿", display_text="템플릿"),
    "fee_source_url": st.column_config.LinkColumn("비용 출처", display_text="출처"),
    "metric_source_url": st.column_config.LinkColumn("지표 출처", display_text="출처"),
    "official_homepage_url": st.column_config.LinkColumn("홈페이지", display_text="홈"),
    "url": st.column_config.LinkColumn("URL", display_text="link"),
    "last_year_cfp_url": st.column_config.LinkColumn("작년 CFP", display_text="작년 CFP"),
    "current_year_homepage_url": st.column_config.LinkColumn("올해 홈", display_text="올해 홈"),
}


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
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def dday(value: str):
    d = to_date(value)
    return None if d is None else (d - TODAY).days


def dday_label(value: str) -> str:
    n = dday(value)
    if n is None:
        return ""
    if n < 0:
        return f"마감 지남 D+{-n}"
    if n == 0:
        return "오늘 마감"
    return f"D-{n}"


def urgency(value: str) -> str:
    n = dday(value)
    if n is None:
        return "날짜 없음"
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


def style_urgency(df: pd.DataFrame, col: str = "긴급도"):
    colors = {
        "7일 이내": "background-color:#7f1d1d;color:#fee2e2",
        "30일 이내": "background-color:#78350f;color:#ffedd5",
        "60일 이내": "background-color:#713f12;color:#fef3c7",
        "마감 지남": "color:#94a3b8",
    }

    def _row(row):
        return [colors.get(row.get(col, ""), "")] * len(row)

    return df.style.apply(_row, axis=1)


def numeric_amount(value: str):
    if not value:
        return None
    match = re.search(r"[\d,.]+", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def to_krw(amount: str, currency: str):
    value = numeric_amount(amount)
    rate = KRW_RATES.get(str(currency).upper(), None)
    if value is None or rate is None:
        return ""
    return int(round(value * rate / 1000) * 1000)


def fmt_krw(value) -> str:
    if value == "" or value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return f"{int(value):,}원"


def venue_level(row: pd.Series) -> str:
    bits = []
    if row.get("sci_status") or row.get("scie_status") or row.get("ssci_status") or row.get("ahci_status"):
        indexed = [name for name, col in [
            ("SCI", "sci_status"), ("SCIE", "scie_status"), ("SSCI", "ssci_status"), ("AHCI", "ahci_status")
        ] if row.get(col)]
        bits.append("/".join(indexed))
    if row.get("scopus_status"):
        bits.append(f"Scopus {row.get('scopus_status')}")
    if row.get("core_ranking"):
        bits.append(f"CORE {row.get('core_ranking')}")
    if row.get("impact_factor"):
        bits.append(f"IF {row.get('impact_factor')}")
    if row.get("cite_score"):
        bits.append(f"CiteScore {row.get('cite_score')}")
    if row.get("h5_index"):
        bits.append(f"h5 {row.get('h5_index')}")
    if row.get("acceptance_rate"):
        bits.append(f"acceptance {row.get('acceptance_rate')}")
    return " · ".join(bits) if bits else "지표 미확인"


def normalize_scope(scope: str) -> str:
    return {
        "core": "핵심 후보",
        "secondary": "보조 후보",
        "project_specific_only": "특정 주제용",
    }.get(scope, scope or "미분류")


def tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9가-힣+#.-]{2,}", text or "")]


def keyword_rank(keywords: str, base: pd.DataFrame) -> pd.DataFrame:
    query = tokens(keywords)
    if not query:
        return base.assign(match_score=0, matched_keywords="", match_basis="")

    rows = []
    for _, row in base.iterrows():
        text_parts = [
            row.get("acronym", ""), row.get("venue_name", ""), row.get("venue_type", ""),
            row.get("field", ""), row.get("primary_relevance", ""), row.get("secondary_relevance", ""),
            row.get("domain_fit_notes", ""), row.get("typical_submission_types", ""),
            row.get("track_name", ""), row.get("submission_type", ""), row.get("notes", ""),
        ]
        haystack = " ".join(text_parts).lower()
        matched = []
        score = 0
        for q in query:
            if q in haystack:
                matched.append(q)
                score += 3 if q in row.get("primary_relevance", "").lower() else 1
        if row.get("priority_scope") == "core":
            score += 2
        elif row.get("priority_scope") == "secondary":
            score += 1
        if row.get("status") in ("open", "upcoming", "rolling"):
            score += 1
        out = row.to_dict()
        out["match_score"] = score
        out["matched_keywords"] = ", ".join(sorted(set(matched)))
        out["match_basis"] = " / ".join([p for p in text_parts[:8] if p][:4])
        rows.append(out)
    return pd.DataFrame(rows).sort_values(["match_score", "paper_deadline"], ascending=[False, True])


venues = load("venues.csv")
opps = load("opportunities.csv")
fees = load("fees.csv")
metrics = load("metrics.csv")
sources = load("sources.csv")
projects = load("projects.csv")
fits = load("project_opportunity_fit.csv")
watch = load("watchlist.csv")

latest_metric = metrics.copy()
latest_metric["_year"] = pd.to_numeric(latest_metric["metric_year"], errors="coerce").fillna(0)
latest_metric = latest_metric.sort_values("_year").groupby("venue_id", as_index=False).tail(1)
latest_metric["level_summary"] = latest_metric.apply(venue_level, axis=1)

ov = (
    opps.merge(
        venues[
            [
                "venue_id", "acronym", "venue_name", "venue_type", "field", "priority_scope",
                "primary_relevance", "secondary_relevance", "domain_fit_notes", "typical_submission_types",
            ]
        ],
        on="venue_id",
        how="left",
    )
    .merge(latest_metric[["venue_id", "level_summary"]], on="venue_id", how="left")
    .fillna("")
)
ov["학회수준"] = ov["level_summary"].replace("", "지표 미확인")
ov["범위"] = ov["priority_scope"].map(normalize_scope)
ov["D-day"] = ov["paper_deadline"].map(dday_label)
ov["긴급도"] = ov["paper_deadline"].map(urgency)
ov["마감_KST_기준"] = ov.apply(
    lambda r: f"{r['paper_deadline']} {r['deadline_time'] or ''} {r['deadline_timezone'] or ''}".strip(),
    axis=1,
)

st.title("📌 학회/저널 투고 대시보드")
st.caption(
    f"오늘: {TODAY.isoformat()} KST · 공개 CFP/공식 출처 기반 · 비용은 원화 환산 열로 함께 표시"
)

main_tabs = ["오늘 할 일", "마감 캘린더", "키워드 매칭", "기회 비교", "비용(KRW)", "Watchlist"]
if show_admin:
    main_tabs += ["관리자 점검", "AI 제안", "기존 Fit 편집"]
tabs = st.tabs(main_tabs)

with tabs[0]:
    st.subheader("오늘 볼 것만")
    open_up = ov[ov["status"].isin(["open", "upcoming"])].copy()
    open_up["_d"] = pd.to_numeric(open_up["paper_deadline"].map(dday), errors="coerce")
    soon = open_up[(open_up["_d"] >= 0) & (open_up["_d"] <= 30)].sort_values("_d")
    verify_now = open_up[open_up["verification_status"] == "needs_verification"]
    overdue_open = ov[(ov["status"] == "open") & ov["paper_deadline"].map(lambda s: (dday(s) is not None) and dday(s) < 0)]
    wdue = watch[watch["next_check_date"].map(lambda s: (to_date(s) is not None) and to_date(s) <= TODAY)]
    wdue = wdue.merge(venues[["venue_id", "acronym"]], on="venue_id", how="left").fillna("")
    pending = 0
    pu = DATA / "proposed_updates"
    for p in sorted(pu.glob("*.csv")) if pu.exists() else []:
        try:
            pending += len(pd.read_csv(p, dtype=str).fillna(""))
        except Exception:
            pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("30일 내 마감", len(soon))
    c2.metric("확인 필요", len(verify_now) + len(overdue_open))
    c3.metric("Watchlist 예정", len(wdue))
    c4.metric("AI 제안 대기", pending)

    cols_s = [
        "acronym", "track_name", "submission_type", "마감_KST_기준", "D-day",
        "범위", "학회수준", "status", "verification_status", "official_cfp_url",
    ]
    st.markdown("**30일 내 마감**")
    st.dataframe(
        style_urgency(soon[cols_s], "D-day") if len(soon) else soon[cols_s],
        use_container_width=True,
        hide_index=True,
        column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
    )

    with st.expander("확인/정리 필요 항목"):
        st.markdown("마감이 지났는데 open인 항목")
        st.dataframe(
            overdue_open[["acronym", "track_name", "paper_deadline", "official_cfp_url"]],
            use_container_width=True,
            hide_index=True,
            column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
        )
        st.markdown("공식 확인이 필요한 항목")
        st.dataframe(
            verify_now[["acronym", "track_name", "official_cfp_url", "notes"]],
            use_container_width=True,
            hide_index=True,
            column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
        )
        st.markdown("Watchlist 확인일 도래")
        st.dataframe(
            wdue[["watch_id", "acronym", "current_status", "next_check_date", "current_year_homepage_url", "notes"]],
            use_container_width=True,
            hide_index=True,
            column_config={"current_year_homepage_url": LINK_COLS["current_year_homepage_url"]},
        )

with tabs[1]:
    st.subheader("마감 캘린더")
    ics_path = ROOT / "public" / "submission_deadlines.ics"
    try:
        sub_url = json.loads((ROOT / "config" / "calendar.json").read_text(encoding="utf-8")).get("ics_public_url", "")
    except Exception:
        sub_url = ""
    left, right = st.columns(2)
    if sub_url:
        webcal = sub_url.replace("https://", "webcal://")
        gcal = "https://calendar.google.com/calendar/r?cid=" + quote(webcal, safe="")
        outlook = "https://outlook.live.com/calendar/0/addfromweb?url=" + quote(sub_url, safe="") + "&name=" + quote("투고 마감 캘린더")
        left.link_button("Google Calendar 구독", gcal, use_container_width=True)
        left.link_button("Outlook 구독", outlook, use_container_width=True)
        with left.expander("수동 구독 URL"):
            st.code(sub_url, language=None)
    else:
        left.info("config/calendar.json의 ics_public_url을 채우면 구독 버튼이 표시됩니다.")
    if ics_path.exists():
        mtime = datetime.fromtimestamp(ics_path.stat().st_mtime, KST).strftime("%Y-%m-%d %H:%M KST")
        right.caption(f"ICS 마지막 생성: {mtime}")
        right.download_button("ICS 다운로드", ics_path.read_bytes(), "submission_deadlines.ics", "text/calendar")
    else:
        right.caption("ICS 미생성: python scripts/export_calendar.py")

    events = []
    for _, r in ov.iterrows():
        for col, label in [
            ("abstract_deadline", "초록"),
            ("paper_deadline", "논문"),
            ("notification_date", "결과 발표"),
            ("camera_ready_deadline", "최종본"),
            ("conference_start", "학회 시작"),
        ]:
            if r.get(col):
                events.append({
                    "date": r[col],
                    "event": label,
                    "venue": r["acronym"],
                    "track": r["track_name"],
                    "status": r["status"],
                    "timezone": r["deadline_timezone"],
                    "D-day": dday_label(r[col]),
                    "긴급도": urgency(r[col]),
                    "CFP": r["official_cfp_url"],
                })
    cal = pd.DataFrame(events)
    if cal.empty:
        st.info("표시할 일정이 없습니다.")
    else:
        c1, c2, c3 = st.columns(3)
        show_past = c1.checkbox("지난 일정 포함", value=False)
        ev_sel = c2.multiselect("이벤트", sorted(cal["event"].unique()), default=["초록", "논문"])
        within = c3.selectbox("기간", ["전체", "7일 이내", "30일 이내", "60일 이내"])
        view = cal[cal["event"].isin(ev_sel)] if ev_sel else cal
        if not show_past:
            view = view[view["긴급도"] != "마감 지남"]
        if within != "전체":
            lim = {"7일 이내": 7, "30일 이내": 30, "60일 이내": 60}[within]
            view = view[view["date"].map(lambda s: (dday(s) is not None) and 0 <= dday(s) <= lim)]
        view = view.sort_values("date")
        st.dataframe(
            style_urgency(view, "긴급도"),
            use_container_width=True,
            hide_index=True,
            column_config={"CFP": st.column_config.LinkColumn("CFP", display_text="CFP")},
        )

with tabs[2]:
    st.subheader("키워드로 맞는 학회/트랙 찾기")
    st.caption("프로젝트를 미리 지정하지 않고, 학회/트랙의 분야·주제·노트·투고유형 DB에서 키워드 매칭으로 정렬합니다.")
    q = st.text_input("키워드", placeholder="예: human-ai interaction, trust, mobile banking, accessibility, field study")
    c1, c2, c3 = st.columns(3)
    only_active = c1.checkbox("열려 있거나 예정/롤링만", value=True)
    min_score = c2.slider("최소 매칭 점수", 0, 10, 1)
    max_rows = c3.number_input("표시 개수", min_value=5, max_value=100, value=30, step=5)
    ranked = keyword_rank(q, ov)
    if only_active:
        ranked = ranked[ranked["status"].isin(["open", "upcoming", "rolling"])]
    ranked = ranked[ranked["match_score"] >= min_score].head(int(max_rows))
    cols = [
        "match_score", "matched_keywords", "acronym", "track_name", "submission_type",
        "마감_KST_기준", "D-day", "범위", "학회수준", "match_basis", "official_cfp_url",
    ]
    st.dataframe(
        ranked[cols],
        use_container_width=True,
        hide_index=True,
        column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
    )
    st.info("추천 아이디어: 이 화면을 키워드 저장/알림 기능과 연결하면, 새 CFP가 들어왔을 때 관심 키워드별 후보를 자동 digest에 넣을 수 있습니다.")

with tabs[3]:
    st.subheader("기회 비교")
    f1, f2, f3, f4 = st.columns(4)
    fld = f1.multiselect("분야", sorted(v for v in ov["field"].unique() if v))
    vtype = f2.multiselect("유형", sorted(v for v in ov["venue_type"].unique() if v))
    stype = f3.multiselect("투고 유형", sorted(v for v in ov["submission_type"].unique() if v))
    stat = f4.multiselect("상태", sorted(v for v in ov["status"].unique() if v), default=[s for s in ["open", "rolling", "upcoming"] if s in set(ov["status"])])
    g1, g2, g3, g4 = st.columns(4)
    scope = g1.multiselect("우선순위", sorted(v for v in ov["priority_scope"].unique() if v), default=[s for s in ["core", "secondary"] if s in set(ov["priority_scope"])])
    only_indexed = g2.checkbox("지표 확인된 학회만")
    dl_from = g3.date_input("마감 시작", value=None)
    dl_to = g4.date_input("마감 끝", value=None)

    view = ov.copy()
    if fld:
        view = view[view["field"].isin(fld)]
    if vtype:
        view = view[view["venue_type"].isin(vtype)]
    if stype:
        view = view[view["submission_type"].isin(stype)]
    if stat:
        view = view[view["status"].isin(stat)]
    if scope:
        view = view[view["priority_scope"].isin(scope)]
    if only_indexed:
        view = view[view["학회수준"] != "지표 미확인"]
    if dl_from:
        view = view[view["paper_deadline"].map(lambda s: (to_date(s) or datetime.max.date()) >= dl_from)]
    if dl_to:
        view = view[view["paper_deadline"].map(lambda s: (to_date(s) or datetime.min.date()) <= dl_to)]
    cols = [
        "acronym", "track_name", "submission_type", "year", "마감_KST_기준", "D-day",
        "location_city", "location_country", "online_hybrid", "page_limit", "word_limit",
        "status", "범위", "학회수준", "verification_status", "official_cfp_url",
        "deadline_source_url", "template_url", "notes", "긴급도",
    ]
    view = view.sort_values(["status", "paper_deadline"])
    st.dataframe(
        style_urgency(view[cols], "긴급도"),
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in LINK_COLS.items() if k in cols},
    )
    st.caption(f"{len(view)}건 표시")

with tabs[4]:
    st.subheader("비용 비교")
    fview = (
        fees.merge(venues[["venue_id", "acronym", "venue_type"]], on="venue_id", how="left")
        .merge(opps[["opportunity_id", "track_name", "location_city", "location_country", "online_hybrid"]], on="opportunity_id", how="left")
        .fillna("")
    )
    fview["amount_krw"] = fview.apply(lambda r: to_krw(r["amount"], r["currency"]), axis=1)
    fview["원화환산"] = fview["amount_krw"].map(fmt_krw)
    c1, c2 = st.columns(2)
    ftype = c1.multiselect("비용 유형", sorted(v for v in fview["fee_type"].unique() if v))
    fcat = c2.multiselect("구분", sorted(v for v in fview["category"].unique() if v))
    if ftype:
        fview = fview[fview["fee_type"].isin(ftype)]
    if fcat:
        fview = fview[fview["category"].isin(fcat)]
    cols = [
        "acronym", "track_name", "fee_type", "category", "amount", "currency", "원화환산",
        "fee_deadline", "location_city", "location_country", "online_hybrid",
        "fee_source_url", "last_checked_at", "verification_status", "notes",
    ]
    st.dataframe(
        fview[cols],
        use_container_width=True,
        hide_index=True,
        column_config={"fee_source_url": LINK_COLS["fee_source_url"]},
    )
    st.caption("환율은 앱 내부 기본값을 사용한 참고용 환산입니다. 정확한 정산 전에는 공식 결제 페이지와 카드사 환율을 확인하세요.")

with tabs[5]:
    st.subheader("Watchlist")
    wview = watch.merge(venues[["venue_id", "acronym", "venue_name"]], on="venue_id", how="left").fillna("")
    wview["확인필요"] = wview["next_check_date"].map(lambda s: "확인 필요" if (to_date(s) is not None and to_date(s) <= TODAY) else "")
    cols = [
        "watch_id", "acronym", "venue_name", "expected_cycle", "expected_submission_month",
        "current_status", "last_checked_at", "next_check_date", "확인필요",
        "last_year_cfp_url", "current_year_homepage_url", "notes",
    ]
    st.dataframe(
        wview[cols].sort_values("next_check_date"),
        use_container_width=True,
        hide_index=True,
        column_config={k: v for k, v in LINK_COLS.items() if k in cols},
    )
    st.metric("오늘 기준 확인 필요", int((wview["확인필요"] != "").sum()))

if show_admin:
    admin_offset = 6
    with tabs[admin_offset]:
        st.subheader("관리자 점검")

        def show_issues(title: str, df: pd.DataFrame, cols=None):
            st.markdown(f"**{title}: {len(df)}건**")
            if len(df):
                view_df = df if cols is None else df[[c for c in cols if c in df.columns]]
                st.dataframe(view_df, use_container_width=True, hide_index=True, column_config={k: v for k, v in LINK_COLS.items() if k in view_df.columns})

        has_dl = (opps["abstract_deadline"] != "") | (opps["paper_deadline"] != "")
        no_dl_url = opps[has_dl & (opps["deadline_source_url"] == "") & (opps["official_cfp_url"] == "")]
        show_issues("마감은 있는데 출처 URL이 없는 기회", no_dl_url, ["opportunity_id", "track_name", "paper_deadline", "notes"])
        bad_fee = fees[(fees["amount"] != "") & (fees["fee_source_url"] == "")]
        show_issues("금액은 있는데 비용 출처가 없는 항목", bad_fee)
        has_metric = (metrics["impact_factor"] != "") | (metrics["cite_score"] != "") | (metrics["acceptance_rate"] != "") | (metrics["core_ranking"] != "") | (metrics["h5_index"] != "")
        bad_met = metrics[has_metric & ((metrics["metric_source_url"] == "") | (metrics["metric_year"] == ""))]
        show_issues("지표는 있는데 출처/연도가 없는 항목", bad_met)
        stale_frames = []
        for name, df in [("opportunities", opps), ("venues", venues), ("fees", fees), ("metrics", metrics), ("watchlist", watch)]:
            if "last_checked_at" in df.columns:
                s = df[df["last_checked_at"].map(is_stale)].copy()
                if len(s):
                    s.insert(0, "table", name)
                    idc = [c for c in s.columns if c.endswith("_id")][:1]
                    stale_frames.append(s[["table"] + idc + ["last_checked_at"]])
        stale = pd.concat(stale_frames) if stale_frames else pd.DataFrame()
        show_issues(f"last_checked_at {STALE_DAYS}일 초과", stale)

    with tabs[admin_offset + 1]:
        st.subheader("AI 제안 검토")
        st.caption("data/proposed_updates/*.csv의 변경안을 검토한 뒤 결정 CSV를 내려받아 apply_updates.py로 병합합니다.")
        pu = DATA / "proposed_updates"
        keys = {"venues": "venue_id", "opportunities": "opportunity_id", "fees": "fee_id", "metrics": "metric_id", "sources": "source_id", "watchlist": "watch_id", "projects": "project_id"}
        masters = {"venues": venues, "opportunities": opps, "fees": fees, "metrics": metrics, "sources": sources, "watchlist": watch, "projects": projects, "project_opportunity_fit": fits}

        def row_key(row, table):
            if table == "project_opportunity_fit":
                return f"{row.get('project_id', '')}->{row.get('opportunity_id', '')}"
            return row.get(keys[table], "")

        patches = sorted(pu.glob("*.csv")) if pu.exists() else []
        if not patches:
            st.info("대기 중인 제안 파일이 없습니다.")
        for p in patches:
            table = p.stem
            st.markdown(f"### {p.name}")
            prop = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
            master = masters.get(table)
            if master is None:
                st.warning(f"알 수 없는 테이블명: {table}")
                continue
            mk = {row_key(mr, table): mr for _, mr in master.iterrows()}
            rows = []
            for _, r in prop.iterrows():
                k = row_key(r, table)
                old = mk.get(k)
                if old is not None:
                    diffs = [f"{c}: '{old.get(c, '')}' -> '{r[c]}'" for c in prop.columns if c in master.columns and str(old.get(c, "")) != str(r[c])]
                    rows.append({"key": k, "change": "update", "diff": "; ".join(diffs) or "변경 없음", "ai_confidence": r.get("ai_confidence", ""), "change_note": r.get("change_note", "")})
                else:
                    rows.append({"key": k, "change": "add", "diff": "신규", "ai_confidence": r.get("ai_confidence", ""), "change_note": r.get("change_note", "")})
            review = pd.DataFrame(rows)
            review["decision"] = "needs_check"
            decided = st.data_editor(
                review,
                use_container_width=True,
                hide_index=True,
                disabled=[c for c in review.columns if c != "decision"],
                column_config={"decision": st.column_config.SelectboxColumn("decision", options=["accept", "skip", "needs_check"])},
                key=f"decision_{p.stem}",
            )
            dec_out = decided.assign(table=table, decided_at=TODAY.isoformat(), reviewer="")[["table", "key", "change", "decision", "ai_confidence", "change_note", "decided_at", "reviewer"]]
            st.download_button("결정 CSV 다운로드", dec_out.to_csv(index=False).encode("utf-8-sig"), "proposed_updates_decisions.csv", "text/csv", key=f"dl_{p.stem}")
            st.code("python scripts/apply_updates.py --apply --decisions data/proposed_updates_decisions.csv", language="bash")

    with tabs[admin_offset + 2]:
        st.subheader("기존 프로젝트 Fit 편집")
        st.caption("새 추천 방식은 키워드 매칭이 기본입니다. 이 화면은 기존 project_opportunity_fit.csv 유지보수용입니다.")
        w = load_weights()
        pid = st.selectbox("프로젝트", ["(전체)"] + projects["project_id"].tolist())
        fv = fits.copy()
        if pid != "(전체)":
            fv = fv[fv["project_id"] == pid]
        ctx = ov[["opportunity_id", "acronym", "track_name", "paper_deadline", "status", "official_cfp_url"]].rename(columns={"status": "opp_status"})
        fv = fv.merge(ctx, on="opportunity_id", how="left").fillna("")
        fv["D-day"] = fv["paper_deadline"].map(dday_label)
        score_cols = ["fit_score", "submission_probability", "strategic_value", "publication_value", "effort_required", "cost_burden"]

        def calc_priority(df: pd.DataFrame):
            out = []
            for _, r in df.iterrows():
                vals = {}
                for c in score_cols:
                    try:
                        vals[c] = float(r[c]) if str(r[c]).strip() else 0
                    except ValueError:
                        vals[c] = 0
                score = (
                    vals["fit_score"] * w["fit_score"]
                    + vals["strategic_value"] * w["strategic_value"]
                    + vals["submission_probability"] * w["submission_probability"]
                    + vals["publication_value"] * w["publication_value"]
                    + vals["effort_required"] * w["effort_required"]
                    + vals["cost_burden"] * w["cost_burden"]
                )
                out.append(round(score, 2))
            return out

        fit_schema = list(fits.columns)
        context_cols = ["acronym", "track_name", "paper_deadline", "D-day", "opp_status", "official_cfp_url"]
        edited = st.data_editor(
            fv[context_cols + [c for c in fit_schema if c != "priority"]],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            disabled=context_cols,
            column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
            key="fit_editor",
        ).fillna("")
        edited["priority"] = calc_priority(edited)
        rank = edited.assign(_p=pd.to_numeric(edited["priority"], errors="coerce")).sort_values("_p", ascending=False)
        st.dataframe(rank[["project_id", "acronym", "track_name", "fit_score", "strategic_value", "submission_probability", "publication_value", "effort_required", "cost_burden", "priority"]], use_container_width=True, hide_index=True)
        out = edited[fit_schema]
        st.download_button("저장용 CSV 다운로드", out.to_csv(index=False).encode("utf-8-sig"), "project_opportunity_fit.csv", "text/csv")

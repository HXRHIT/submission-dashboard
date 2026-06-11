# -*- coding: utf-8 -*-
"""학회/저널 투고 후보 대시보드 (공개 정보 전용).

실행:  streamlit run dashboard/app.py
배포:  Streamlit Community Cloud — main file path를 dashboard/app.py로 지정.

보안 원칙: 이 앱과 CSV에는 공개 정보와 익명 프로젝트 코드만 둔다.
자세한 내용은 docs/security_policy.md 참고.
"""
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG = ROOT / "config" / "weights.json"

st.set_page_config(page_title="Submission Dashboard", page_icon="📅", layout="wide")

TODAY = date.today()
STALE_DAYS = 60

LINK_COLS = {
    "official_cfp_url": st.column_config.LinkColumn("CFP", display_text="CFP"),
    "deadline_source_url": st.column_config.LinkColumn("마감 출처", display_text="출처"),
    "submission_system_url": st.column_config.LinkColumn("제출 시스템", display_text="제출"),
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
    default = {"fit_score": 0.30, "strategic_value": 0.25, "submission_probability": 0.20,
               "publication_value": 0.15, "effort_required": -0.05, "cost_burden": -0.05}
    try:
        return {**default, **json.loads(CONFIG.read_text(encoding="utf-8"))}
    except Exception:
        return default


def to_date(s):
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def dday(s):
    d = to_date(s)
    if d is None:
        return None
    return (d - TODAY).days


def dday_label(s):
    n = dday(s)
    if n is None:
        return ""
    if n < 0:
        return f"마감 지남 (D+{-n})"
    if n == 0:
        return "오늘 마감 (D-0)"
    return f"D-{n}"


def urgency(s):
    n = dday(s)
    if n is None:
        return "no_date"
    if n < 0:
        return "past"
    if n <= 7:
        return "≤7일"
    if n <= 30:
        return "≤30일"
    if n <= 60:
        return "≤60일"
    return "60일+"


def is_stale(s):
    d = to_date(s)
    return d is not None and (TODAY - d).days > STALE_DAYS


def style_urgency(df, col="urgency"):
    colors = {"≤7일": "background-color:#ffcccc", "≤30일": "background-color:#ffe5b4",
              "≤60일": "background-color:#fff7c0", "past": "color:#999999"}

    def _row(r):
        c = colors.get(r.get(col, ""), "")
        return [c] * len(r)

    return df.style.apply(_row, axis=1)


venues = load("venues.csv")
opps = load("opportunities.csv")
fees = load("fees.csv")
metrics = load("metrics.csv")
sources = load("sources.csv")
projects = load("projects.csv")
fits = load("project_opportunity_fit.csv")
watch = load("watchlist.csv")

# joined opportunities + venue info
ov = opps.merge(
    venues[["venue_id", "acronym", "venue_name", "venue_type", "field", "priority_scope",
            "primary_relevance"]],
    on="venue_id", how="left",
).fillna("")

st.title("📅 학회/저널 투고 후보 대시보드")
st.caption(
    f"오늘: {TODAY.isoformat()} · 공개 정보 전용 · 모든 값은 출처 URL과 함께 관리 "
    "(URL 없는 값은 needs_verification)"
)

tabs = st.tabs(["🗓 투고 캘린더", "📊 후보 비교표", "🎯 프로젝트 Fit", "🔍 URL 검증",
                "💰 비용 비교", "📈 수준 지표", "👀 Watchlist"])

# ---------------------------------------------------------------- 1. calendar
with tabs[0]:
    st.subheader("전체 투고 캘린더")
    events = []
    for _, r in ov.iterrows():
        for col, label in [("abstract_deadline", "abstract"), ("paper_deadline", "paper"),
                           ("notification_date", "notification"),
                           ("camera_ready_deadline", "camera-ready"),
                           ("conference_start", "conference")]:
            if r[col]:
                events.append({
                    "date": r[col], "event": label, "venue": r["acronym"],
                    "track": r["track_name"], "submission_type": r["submission_type"],
                    "status": r["status"], "deadline_timezone": r["deadline_timezone"],
                    "verification_status": r["verification_status"],
                    "official_cfp_url": r["official_cfp_url"],
                    "deadline_source_url": r["deadline_source_url"],
                })
    cal = pd.DataFrame(events)
    if cal.empty:
        st.info("표시할 일정이 없습니다.")
    else:
        cal["D-day"] = cal["date"].map(dday_label)
        cal["urgency"] = cal["date"].map(urgency)
        c1, c2, c3 = st.columns(3)
        show_past = c1.checkbox("마감 지난 항목 포함", value=False)
        ev_sel = c2.multiselect("이벤트 종류", sorted(cal["event"].unique()),
                                default=["abstract", "paper"])
        within = c3.selectbox("기간 강조", ["전체", "7일 이내", "30일 이내", "60일 이내"])
        view = cal[cal["event"].isin(ev_sel)] if ev_sel else cal
        if not show_past:
            view = view[view["urgency"] != "past"]
        if within != "전체":
            lim = {"7일 이내": 7, "30일 이내": 30, "60일 이내": 60}[within]
            view = view[view["date"].map(lambda s: (dday(s) is not None) and 0 <= dday(s) <= lim)]
        view = view.sort_values("date")
        n7 = (view["urgency"] == "≤7일").sum()
        n30 = (view["urgency"].isin(["≤7일", "≤30일"])).sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("7일 이내 마감", int(n7))
        m2.metric("30일 이내 마감", int(n30))
        m3.metric("표시 중인 일정", len(view))
        st.dataframe(
            style_urgency(view.drop(columns=["urgency"]).assign(urgency=view["urgency"])),
            use_container_width=True, hide_index=True,
            column_config={k: v for k, v in LINK_COLS.items() if k in view.columns},
        )
        st.caption("빨강 ≤7일 · 주황 ≤30일 · 노랑 ≤60일 · 회색 = 마감 지남. "
                   "ICS 캘린더 내보내기: `python scripts/export_calendar.py`")

# ---------------------------------------------------------------- 2. compare
with tabs[1]:
    st.subheader("후보 비교표")
    f1, f2, f3, f4 = st.columns(4)
    fld = f1.multiselect("분야(field)", sorted(v for v in ov["field"].unique() if v))
    vtype = f2.multiselect("venue type", sorted(v for v in ov["venue_type"].unique() if v))
    stype = f3.multiselect("submission type", sorted(v for v in ov["submission_type"].unique() if v))
    yr = f4.multiselect("연도", sorted(v for v in ov["year"].unique() if v))
    f5, f6, f7, f8 = st.columns(4)
    ctry = f5.multiselect("국가", sorted(v for v in ov["location_country"].unique() if v))
    stat = f6.multiselect("status", sorted(v for v in ov["status"].unique() if v),
                          default=[s for s in ["open", "rolling", "upcoming"] if s in set(ov["status"])])
    verif = f7.multiselect("verification", sorted(v for v in ov["verification_status"].unique() if v))
    scope = f8.multiselect("priority scope", sorted(v for v in ov["priority_scope"].unique() if v),
                           default=[s for s in ["core", "secondary"] if s in set(ov["priority_scope"])])
    f9, f10 = st.columns(2)
    dl_from = f9.date_input("마감일 시작", value=None)
    dl_to = f10.date_input("마감일 끝", value=None)

    # metrics-based filters (있는 값 기준)
    met_idx = metrics[metrics["venue_id"] != ""].copy()
    has_if = set(met_idx.loc[met_idx["impact_factor"] != "", "venue_id"])
    has_scopus = set(met_idx.loc[met_idx["scopus_status"] != "", "venue_id"])
    has_core = set(met_idx.loc[met_idx["core_ranking"] != "", "venue_id"])
    g1, g2, g3 = st.columns(3)
    only_if = g1.checkbox("IF 확인된 venue만")
    only_scopus = g2.checkbox("Scopus 확인된 venue만")
    only_core = g3.checkbox("CORE ranking 확인된 venue만")

    view = ov.copy()
    if fld: view = view[view["field"].isin(fld)]
    if vtype: view = view[view["venue_type"].isin(vtype)]
    if stype: view = view[view["submission_type"].isin(stype)]
    if yr: view = view[view["year"].isin(yr)]
    if ctry: view = view[view["location_country"].isin(ctry)]
    if stat: view = view[view["status"].isin(stat)]
    if verif: view = view[view["verification_status"].isin(verif)]
    if scope: view = view[view["priority_scope"].isin(scope)]
    if dl_from: view = view[view["paper_deadline"].map(lambda s: (to_date(s) or date.max) >= dl_from)]
    if dl_to: view = view[view["paper_deadline"].map(lambda s: (to_date(s) or date.min) <= dl_to)]
    if only_if: view = view[view["venue_id"].isin(has_if)]
    if only_scopus: view = view[view["venue_id"].isin(has_scopus)]
    if only_core: view = view[view["venue_id"].isin(has_core)]

    # 비용/지표 출처 URL 붙이기 (venue 기준 첫 행)
    fee_url = fees[fees["fee_source_url"] != ""].groupby("venue_id")["fee_source_url"].first()
    met_url = metrics[metrics["metric_source_url"] != ""].groupby("venue_id")["metric_source_url"].first()
    view = view.assign(
        fee_source_url=view["venue_id"].map(fee_url).fillna(""),
        metric_source_url=view["venue_id"].map(met_url).fillna(""),
        **{"D-day": view["paper_deadline"].map(dday_label)},
        urgency=view["paper_deadline"].map(urgency),
    )
    cols = ["acronym", "track_name", "submission_type", "year", "abstract_deadline",
            "paper_deadline", "deadline_timezone", "D-day", "location_city",
            "location_country", "online_hybrid", "page_limit", "word_limit", "status",
            "priority_scope", "verification_status", "official_cfp_url",
            "deadline_source_url", "submission_system_url", "template_url",
            "fee_source_url", "metric_source_url", "notes", "urgency"]
    view = view.sort_values(["status", "paper_deadline"])
    st.dataframe(style_urgency(view[cols]), use_container_width=True, hide_index=True,
                 column_config={k: v for k, v in LINK_COLS.items() if k in cols})
    st.caption(f"{len(view)}건 표시")

# ---------------------------------------------------------------- 3. fit
with tabs[2]:
    st.subheader("프로젝트별 익명 Fit 관리")
    st.caption("프로젝트는 익명 코드(P01…)와 broad field/method만 사용. "
               "내부 연구 내용은 절대 입력하지 않는다 (docs/security_policy.md).")
    st.dataframe(projects, use_container_width=True, hide_index=True)

    w = load_weights()
    st.markdown(
        "**Priority Score** = "
        f"fit×{w['fit_score']} + strategic×{w['strategic_value']} + "
        f"probability×{w['submission_probability']} + publication×{w['publication_value']} "
        f"− effort×{abs(w['effort_required'])} − cost×{abs(w['cost_burden'])} "
        "(가중치: config/weights.json)"
    )

    pid = st.selectbox("프로젝트 선택", ["(전체)"] + projects["project_id"].tolist())
    fv = fits.copy()
    if pid != "(전체)":
        fv = fv[fv["project_id"] == pid]
    fv = fv.merge(
        ov[["opportunity_id", "acronym", "track_name", "paper_deadline", "status",
            "official_cfp_url"]],
        on="opportunity_id", how="left",
    ).fillna("")
    fv["D-day"] = fv["paper_deadline"].map(dday_label)

    num_cols = ["fit_score", "submission_probability", "strategic_value",
                "publication_value", "effort_required", "cost_burden"]

    def calc_priority(df):
        out = []
        for _, r in df.iterrows():
            try:
                vals = {c: float(r[c]) for c in num_cols if str(r[c]).strip() != ""}
                score = (vals.get("fit_score", 0) * w["fit_score"]
                         + vals.get("strategic_value", 0) * w["strategic_value"]
                         + vals.get("submission_probability", 0) * w["submission_probability"]
                         + vals.get("publication_value", 0) * w["publication_value"]
                         + vals.get("effort_required", 0) * w["effort_required"]
                         + vals.get("cost_burden", 0) * w["cost_burden"])
                out.append(round(score, 2))
            except Exception:
                out.append(None)
        return out

    fv["priority"] = calc_priority(fv)
    show = ["project_id", "acronym", "track_name", "paper_deadline", "D-day", "status_y",
            "fit_score", "fit_rationale_public_safe", "expected_difficulty",
            "submission_probability", "strategic_value", "publication_value",
            "effort_required", "cost_burden", "priority", "risk_tags",
            "next_action_public_safe", "internal_deadline", "status_x", "official_cfp_url"]
    show = [c for c in show if c in fv.columns]
    edited = st.data_editor(
        fv[show].sort_values("priority", ascending=False),
        use_container_width=True, hide_index=True, num_rows="dynamic",
        column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
        key="fit_editor",
    )
    st.caption("status_x = fit 진행 상태, status_y = 트랙 모집 상태")
    c1, c2 = st.columns(2)
    if c1.button("priority 재계산"):
        st.rerun()
    csv_bytes = edited.to_csv(index=False).encode("utf-8-sig")
    c2.download_button("수정본 CSV 다운로드", csv_bytes, "project_opportunity_fit_edited.csv",
                       "text/csv")
    st.info("⚠️ 웹 배포(Streamlit Cloud)에서는 편집 내용이 저장되지 않습니다. "
            "수정본 CSV를 다운로드해 data/project_opportunity_fit.csv 컬럼 구조에 맞게 반영하고 "
            "git commit/push 하세요 (docs/update_guide.md).")

# ---------------------------------------------------------------- 4. URL check
with tabs[3]:
    st.subheader("URL 검증 (허위/노후 정보 제거용)")

    def show_issues(title, df, cols=None):
        st.markdown(f"**{title}** — {len(df)}건")
        if len(df):
            df = df if cols is None else df[[c for c in cols if c in df.columns]]
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={k: v for k, v in LINK_COLS.items() if k in df.columns})
        st.divider()

    has_dl = (opps["abstract_deadline"] != "") | (opps["paper_deadline"] != "")
    no_dl_url = opps[has_dl & (opps["deadline_source_url"] == "") & (opps["official_cfp_url"] == "")]
    show_issues("① deadline은 있는데 출처 URL이 없는 기회", no_dl_url,
                ["opportunity_id", "track_name", "paper_deadline", "notes"])

    bad_fee = fees[(fees["amount"] != "") & (fees["fee_source_url"] == "")]
    show_issues("② 금액은 있는데 fee_source_url이 없는 비용", bad_fee)

    has_metric = (metrics["impact_factor"] != "") | (metrics["cite_score"] != "") | \
                 (metrics["acceptance_rate"] != "") | (metrics["core_ranking"] != "") | \
                 (metrics["h5_index"] != "")
    bad_met = metrics[has_metric & ((metrics["metric_source_url"] == "") | (metrics["metric_year"] == ""))]
    show_issues("③ 지표 값은 있는데 URL 또는 기준연도가 없는 행", bad_met,
                ["metric_id", "venue_id", "metric_year", "impact_factor", "cite_score",
                 "metric_source_url", "notes"])

    src_rel = sources.set_index("url")["reliability"] if "url" in sources.columns else pd.Series(dtype=str)
    nonoff = ov[has_dl.reindex(ov.index, fill_value=False) &
                ov["deadline_source_url"].map(lambda u: u != "" and src_rel.get(u, "") == "low")]
    sec_only = ov[ov["verification_status"] == "secondary_only"]
    show_issues("④ 공식 출처가 아닌(2차 출처/저신뢰) deadline", pd.concat([nonoff, sec_only]).drop_duplicates(),
                ["opportunity_id", "track_name", "paper_deadline", "deadline_source_url",
                 "verification_status"])

    stale_frames = []
    for name, df in [("opportunities", opps), ("venues", venues), ("fees", fees),
                     ("metrics", metrics), ("watchlist", watch)]:
        if "last_checked_at" in df.columns:
            s = df[df["last_checked_at"].map(is_stale)].copy()
            if len(s):
                s.insert(0, "table", name)
                idc = [c for c in s.columns if c.endswith("_id")][:1]
                stale_frames.append(s[["table"] + idc + ["last_checked_at"]])
    stale = pd.concat(stale_frames) if stale_frames else pd.DataFrame()
    show_issues(f"⑤ last_checked_at이 {STALE_DAYS}일 이상 지난 항목", stale)

    nv_frames = []
    for name, df in [("venues", venues), ("opportunities", opps), ("fees", fees), ("metrics", metrics)]:
        if "verification_status" in df.columns:
            s = df[df["verification_status"] == "needs_verification"].copy()
            if len(s):
                s.insert(0, "table", name)
                idc = [c for c in s.columns if c.endswith("_id")][:1]
                keep = ["table"] + idc + [c for c in ["track_name", "venue_name", "notes"] if c in s.columns]
                nv_frames.append(s[keep])
    nv = pd.concat(nv_frames) if nv_frames else pd.DataFrame()
    show_issues("⑥ verification_status = needs_verification", nv)

    low_src = sources[sources["reliability"] == "low"]
    show_issues("⑦ reliability가 low인 출처", low_src)

    overdue = opps[(opps["status"] == "open") &
                   opps["paper_deadline"].map(lambda s: (dday(s) is not None) and dday(s) < 0)]
    show_issues("⑧ 마감이 지났는데 status가 open인 기회", overdue,
                ["opportunity_id", "track_name", "paper_deadline", "official_cfp_url"])

# ---------------------------------------------------------------- 5. fees
with tabs[4]:
    st.subheader("비용 비교 (등록비 / APC)")
    fview = fees.merge(venues[["venue_id", "acronym", "venue_type"]], on="venue_id", how="left") \
                .merge(opps[["opportunity_id", "track_name", "location_city", "location_country",
                             "online_hybrid"]], on="opportunity_id", how="left").fillna("")
    c1, c2 = st.columns(2)
    ftype = c1.multiselect("fee type", sorted(v for v in fview["fee_type"].unique() if v))
    fcat = c2.multiselect("category", sorted(v for v in fview["category"].unique() if v))
    if ftype: fview = fview[fview["fee_type"].isin(ftype)]
    if fcat: fview = fview[fview["category"].isin(fcat)]
    cols = ["acronym", "track_name", "fee_type", "category", "amount", "currency",
            "fee_deadline", "location_city", "location_country", "online_hybrid",
            "fee_source_url", "last_checked_at", "verification_status", "notes"]
    st.dataframe(fview[cols], use_container_width=True, hide_index=True,
                 column_config={"fee_source_url": LINK_COLS["fee_source_url"]})
    st.caption("amount가 빈 항목은 fee_source_url 페이지에서 직접 확인 후 입력하세요. "
               "URL 없는 금액은 입력 금지 (source policy).")

# ---------------------------------------------------------------- 6. metrics
with tabs[5]:
    st.subheader("수준 지표 비교")
    mview = metrics.merge(venues[["venue_id", "acronym", "venue_name", "venue_type", "field"]],
                          on="venue_id", how="left").fillna("")
    only_vals = st.checkbox("값이 있는 행만 보기", value=False)
    if only_vals:
        mview = mview[(mview["impact_factor"] != "") | (mview["cite_score"] != "") |
                      (mview["core_ranking"] != "") | (mview["h5_index"] != "") |
                      (mview["acceptance_rate"] != "")]
    cols = ["acronym", "venue_name", "venue_type", "field", "metric_year", "sci_status",
            "scie_status", "ssci_status", "ahci_status", "scopus_status", "impact_factor",
            "cite_score", "core_ranking", "h5_index", "acceptance_rate",
            "metric_source_url", "metric_source_type", "last_checked_at",
            "verification_status", "notes"]
    st.dataframe(mview[cols], use_container_width=True, hide_index=True,
                 column_config={"metric_source_url": LINK_COLS["metric_source_url"]})
    st.caption("기준연도+URL 없는 지표는 값 입력 금지. SCI/SSCI/Scopus/CORE는 "
               "JCR·Scopus·CORE 포털에서 확인 후 입력 (docs/source_policy.md).")

# ---------------------------------------------------------------- 7. watchlist
with tabs[6]:
    st.subheader("Watchlist — CFP 미공개 venue 추적")
    wview = watch.merge(venues[["venue_id", "acronym", "venue_name"]], on="venue_id", how="left").fillna("")
    wview["check_due"] = wview["next_check_date"].map(
        lambda s: "✅ 확인 필요" if (to_date(s) is not None and to_date(s) <= TODAY) else "")
    cols = ["watch_id", "acronym", "venue_name", "expected_cycle", "expected_submission_month",
            "current_status", "last_checked_at", "next_check_date", "check_due",
            "last_year_cfp_url", "current_year_homepage_url", "notes"]
    st.dataframe(wview[cols].sort_values("next_check_date"), use_container_width=True,
                 hide_index=True,
                 column_config={k: v for k, v in LINK_COLS.items() if k in cols})
    due = int((wview["check_due"] != "").sum())
    st.metric("오늘 기준 확인이 필요한 항목", due)

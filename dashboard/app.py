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
from urllib.parse import quote

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

tabs = st.tabs(["📥 Inbox", "🗓 투고 캘린더", "📊 후보 비교표", "🎯 프로젝트 Fit",
                "🔍 URL 검증", "💰 비용 비교", "📈 수준 지표", "👀 Watchlist",
                "🤖 AI 제안 검토"])

# ---------------------------------------------------------------- 1. Inbox
with tabs[0]:
    st.subheader("📥 이번 주 Inbox — 오늘 해야 할 것만")

    open_up = ov[ov["status"].isin(["open", "upcoming"])].copy()
    open_up["_d"] = pd.to_numeric(open_up["paper_deadline"].map(dday), errors="coerce")
    soon = open_up[(open_up["_d"] >= 0) & (open_up["_d"] <= 30)].sort_values("_d")
    verify_now = open_up[open_up["verification_status"] == "needs_verification"]
    overdue_open = ov[(ov["status"] == "open") &
                      ov["paper_deadline"].map(lambda s: (dday(s) is not None) and dday(s) < 0)]
    wdue = watch[watch["next_check_date"].map(
        lambda s: (to_date(s) is not None) and to_date(s) <= TODAY)]
    wdue = wdue.merge(venues[["venue_id", "acronym"]], on="venue_id", how="left").fillna("")
    _pu = DATA / "proposed_updates"
    _pending = 0
    for _p in (sorted(_pu.glob("*.csv")) if _pu.exists() else []):
        try:
            _pending += len(pd.read_csv(_p, dtype=str).fillna(""))
        except Exception:  # noqa: BLE001
            pass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 Submit soon (≤30일)", len(soon))
    c2.metric("🔍 Verify now", len(verify_now) + len(overdue_open))
    c3.metric("👀 Watchlist due", len(wdue))
    c4.metric("🤖 AI 제안 대기", _pending)

    with st.expander(f"🔥 Submit soon — 30일 이내 마감 {len(soon)}건", expanded=True):
        cols_s = ["acronym", "track_name", "submission_type", "paper_deadline",
                  "deadline_timezone", "status", "verification_status", "official_cfp_url"]
        view_s = soon[cols_s].assign(**{"D-day": soon["paper_deadline"].map(dday_label)})
        st.dataframe(view_s, use_container_width=True, hide_index=True,
                     column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]})
    with st.expander(f"🔍 Verify now — 미확인 {len(verify_now)}건 / 마감 지난 open {len(overdue_open)}건"):
        st.markdown("**needs_verification (open/upcoming)** — 공식 페이지에서 마감 확인 후 입력")
        st.dataframe(verify_now[["acronym", "track_name", "official_cfp_url", "notes"]],
                     use_container_width=True, hide_index=True,
                     column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]})
        st.markdown("**마감 지났는데 open** — status를 closed로 변경")
        st.dataframe(overdue_open[["acronym", "track_name", "paper_deadline",
                                   "official_cfp_url"]],
                     use_container_width=True, hide_index=True,
                     column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]})
    with st.expander(f"👀 Watchlist due — 재확인 {len(wdue)}건"):
        st.dataframe(wdue[["watch_id", "acronym", "current_status", "next_check_date",
                           "current_year_homepage_url", "notes"]],
                     use_container_width=True, hide_index=True,
                     column_config={"current_year_homepage_url":
                                    LINK_COLS["current_year_homepage_url"]})
    with st.expander(f"🤖 AI 제안 대기 — {_pending}행"):
        st.markdown("'🤖 AI 제안 검토' 탭에서 diff 확인 → "
                    "`python scripts/apply_updates.py --list`")
    st.caption("이 화면과 동일한 내용이 매주 digest로 발송됩니다 "
               "(scripts/generate_weekly_digest.py · GitHub Actions weekly-digest).")

# ---------------------------------------------------------------- 2. calendar
with tabs[1]:
    st.subheader("전체 투고 캘린더")

    # 구독형 캘린더 안내
    ics_path = ROOT / "public" / "submission_deadlines.ics"
    try:
        sub_url = json.loads((ROOT / "config" / "calendar.json")
                             .read_text(encoding="utf-8")).get("ics_public_url", "")
    except Exception:  # noqa: BLE001
        sub_url = ""
    s1, s2 = st.columns(2)
    if sub_url:
        webcal = sub_url.replace("https://", "webcal://")
        gcal = "https://calendar.google.com/calendar/r?cid=" + quote(webcal, safe="")
        outlook = ("https://outlook.live.com/calendar/0/addfromweb?url="
                   + quote(sub_url, safe="") + "&name=" + quote("투고 마감 캘린더"))
        o365 = ("https://outlook.office.com/calendar/0/addfromweb?url="
                + quote(sub_url, safe="") + "&name=" + quote("투고 마감 캘린더"))
        s1.markdown("**📅 캘린더 구독** — 클릭하면 구독 화면이 바로 열립니다")
        b1, b2, b3 = s1.columns(3)
        b1.link_button("Google Calendar", gcal, use_container_width=True)
        b2.link_button("Outlook.com", outlook, use_container_width=True)
        b3.link_button("Office 365", o365, use_container_width=True)
        with s1.expander("수동 추가용 URL (구독이 안 열릴 때)"):
            st.code(sub_url, language=None)
            st.caption("Google Calendar → 다른 캘린더 + → 'URL로 추가'에 붙여넣기")
    else:
        s1.info("public/submission_deadlines.ics를 공개 URL에 올리고 "
                "config/calendar.json의 ics_public_url에 넣으면 구독 링크가 표시됩니다 "
                "(docs/update_guide.md §4).")
    if ics_path.exists():
        mtime = datetime.fromtimestamp(ics_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        s2.caption(f"ICS 마지막 생성: {mtime}")
        s2.download_button("ICS 다운로드", ics_path.read_bytes(),
                           "submission_deadlines.ics", "text/calendar")
    else:
        s2.caption("ICS 미생성 — `python scripts/export_calendar.py`")
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

# ---------------------------------------------------------------- 3. compare
with tabs[2]:
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

# ---------------------------------------------------------------- 4. fit
with tabs[3]:
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
    ctx = ov[["opportunity_id", "acronym", "track_name", "paper_deadline", "status",
              "official_cfp_url"]].rename(columns={"status": "opp_status"})
    fv = fv.merge(ctx, on="opportunity_id", how="left").fillna("")
    fv["D-day"] = fv["paper_deadline"].map(dday_label)

    FIT_SCHEMA = list(fits.columns)          # 원본 스키마 (저장용 export 기준)
    CONTEXT_COLS = ["acronym", "track_name", "paper_deadline", "D-day", "opp_status",
                    "official_cfp_url"]      # 표시 전용 — export에서 제외
    SCORE_COLS = ["fit_score", "submission_probability", "strategic_value",
                  "publication_value", "effort_required", "cost_burden"]

    def calc_priority(df):
        out = []
        for _, r in df.iterrows():
            try:
                vals = {c: float(r[c]) for c in SCORE_COLS if str(r[c]).strip() != ""}
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

    editor_cols = CONTEXT_COLS + [c for c in FIT_SCHEMA if c != "priority"]
    edited = st.data_editor(
        fv[editor_cols], use_container_width=True, hide_index=True, num_rows="dynamic",
        disabled=CONTEXT_COLS,
        column_config={"official_cfp_url": LINK_COLS["official_cfp_url"]},
        key="fit_editor",
    ).fillna("")
    st.caption("회색 컬럼은 표시 전용(저장 제외). 점수 컬럼은 1~5.")

    # 편집된 값 기준으로 priority 확정 계산
    edited["priority"] = calc_priority(edited)
    rank = edited.assign(_p=pd.to_numeric(edited["priority"], errors="coerce")) \
                 .sort_values("_p", ascending=False)
    st.markdown("**계산된 Priority (편집 반영 — 저장되는 값)**")
    st.dataframe(
        rank[["project_id", "acronym", "track_name", "fit_score", "strategic_value",
              "submission_probability", "publication_value", "effort_required",
              "cost_burden", "priority"]],
        use_container_width=True, hide_index=True)

    out = edited[FIT_SCHEMA]                 # 원본 컬럼·순서 그대로 (priority 포함)
    csv_bytes = out.to_csv(index=False).encode("utf-8-sig")
    st.download_button("저장용 CSV 다운로드 (project_opportunity_fit.csv 스키마)",
                       csv_bytes, "project_opportunity_fit.csv", "text/csv")
    st.info("⚠️ 웹 배포(Streamlit Cloud)에서는 편집 내용이 저장되지 않습니다. "
            "위 버튼으로 받은 파일을 data/project_opportunity_fit.csv에 그대로 덮어쓰고 "
            "validate → git commit/push 하세요 (docs/update_guide.md). "
            "단, 프로젝트 필터를 건 상태의 다운로드는 해당 프로젝트 행만 포함합니다.")

# ---------------------------------------------------------------- 5. URL check
with tabs[4]:
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

# ---------------------------------------------------------------- 6. fees
with tabs[5]:
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

# ---------------------------------------------------------------- 7. metrics
with tabs[6]:
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

# ---------------------------------------------------------------- 8. watchlist
with tabs[7]:
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

# ---------------------------------------------------------------- 9. AI proposals
with tabs[8]:
    st.subheader("AI 제안 검토 (proposed_updates)")
    st.caption("AI가 만든 수정 초안은 master CSV를 직접 고치지 않고 "
               "data/proposed_updates/<테이블명>.csv 로 둔다. 여기서 diff를 검토한 뒤 "
               "로컬에서 scripts/apply_updates.py 로 병합한다 (검증 실패 시 자동 롤백).")
    PU = DATA / "proposed_updates"
    KEYS = {"venues": "venue_id", "opportunities": "opportunity_id", "fees": "fee_id",
            "metrics": "metric_id", "sources": "source_id", "watchlist": "watch_id",
            "projects": "project_id"}
    MASTERS = {"venues": venues, "opportunities": opps, "fees": fees, "metrics": metrics,
               "sources": sources, "watchlist": watch, "projects": projects,
               "project_opportunity_fit": fits}

    def row_key(row, table):
        if table == "project_opportunity_fit":
            return f"{row.get('project_id', '')}->{row.get('opportunity_id', '')}"
        return row.get(KEYS[table], "")

    patches = sorted(PU.glob("*.csv")) if PU.exists() else []
    if not patches:
        st.info("대기 중인 제안 파일이 없습니다 (data/proposed_updates/*.csv). "
                "형식은 data/proposed_updates/README.md 참고.")
    for p in patches:
        table = p.stem
        st.markdown(f"### 📄 {p.name}")
        try:
            prop = pd.read_csv(p, dtype=str, encoding="utf-8-sig").fillna("")
        except Exception as e:  # noqa: BLE001
            st.error(f"읽기 실패: {e}")
            continue
        master = MASTERS.get(table)
        if master is None:
            st.warning(f"알 수 없는 테이블명: {table} (파일명은 master CSV 이름과 같아야 함)")
            continue
        mk = {}
        for _, mr in master.iterrows():
            mk[row_key(mr, table)] = mr
        rows = []
        for _, r in prop.iterrows():
            k = row_key(r, table)
            old = mk.get(k)
            if old is not None:
                diffs = [f"{c}: '{old.get(c, '')}' -> '{r[c]}'"
                         for c in prop.columns
                         if c in master.columns and str(old.get(c, "")) != str(r[c])]
                rows.append({"key": k, "change": "update",
                             "diff": "; ".join(diffs) or "(변경 없음)",
                             "ai_confidence": r.get("ai_confidence", ""),
                             "change_note": r.get("change_note", "")})
            else:
                rows.append({"key": k, "change": "add", "diff": "(신규 행)",
                             "ai_confidence": r.get("ai_confidence", ""),
                             "change_note": r.get("change_note", "")})
        review = pd.DataFrame(rows)
        review["decision"] = "needs_check"
        decided = st.data_editor(
            review, use_container_width=True, hide_index=True,
            disabled=[c for c in review.columns if c != "decision"],
            column_config={"decision": st.column_config.SelectboxColumn(
                "decision", options=["accept", "skip", "needs_check"],
                help="accept=반영 / skip=폐기 / needs_check=재확인 후 결정")},
            key=f"decision_{p.stem}",
        )
        dec_out = decided.assign(table=table, decided_at=TODAY.isoformat(),
                                 reviewer="")[
            ["table", "key", "change", "decision", "ai_confidence",
             "change_note", "decided_at", "reviewer"]]
        ca, cb = st.columns(2)
        ca.download_button(
            f"결정 CSV 다운로드 ({table})",
            dec_out.to_csv(index=False).encode("utf-8-sig"),
            "proposed_updates_decisions.csv", "text/csv", key=f"dl_{p.stem}")
        n_acc = int((decided["decision"] == "accept").sum())
        cb.metric("accept 선택", f"{n_acc} / {len(decided)}")
        st.code(
            "# 결정 파일 기반 반영 (accept만 병합, 나머지는 패치에 유지)\n"
            "python scripts/apply_updates.py --apply --decisions data/proposed_updates_decisions.csv\n"
            "# 또는 키 직접 지정\n"
            f"python scripts/apply_updates.py --table {table} --apply --only KEY1,KEY2",
            language="bash")
        st.caption("⚠️ 웹 배포에서는 decision이 저장되지 않습니다 — 결정 CSV를 받아 "
                   "data/proposed_updates_decisions.csv로 두고 위 명령으로 반영하세요.")

# end of app

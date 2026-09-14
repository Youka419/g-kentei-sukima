from __future__ import annotations

import pandas as pd
import streamlit as st

from g_study.cheatsheet import (
    add_entry,
    already_has,
    excel_bytes,
    load_excel,
    load_excel_bytes,
    save_both,
    word_bytes,
)
from g_study.config import EXCEL_PATH, OFFICIAL_URL, SYLLABUS_URL, TICKET_URL, WORD_PATH
from g_study.exam import EXAM_OVERVIEW, FEES, NEXT_ONLINE, NEXT_ONSITE_NOTE, NOTES_2026, SCHEDULE_2026, SYLLABUS_TREE
from g_study.progress import (
    chapter_stats,
    daily_quiz_counts,
    load_progress,
    load_progress_bytes,
    progress_bytes,
    record_card,
    record_quiz,
    record_session,
    save_progress,
    weak_terms_from_history,
)
from g_study.quiz import QUIZ_PRESETS, make_quiz
from g_study.runtime import is_cloud
from g_study.terms import all_terms, filter_terms

st.set_page_config(
    page_title="G検定 スキマ学習",
    page_icon="📘",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background: #f4f7fb; }
    .block-container { padding-top: 1rem; padding-bottom: 6rem; max-width: 720px; }
    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid #e5eaf0;
        border-radius: 12px;
        padding: 6px 10px;
    }
    .term-card {
        background: #fff;
        border: 1px solid #dbe3ee;
        border-radius: 16px;
        padding: 1.1rem 1.2rem;
    }
    .muted { color: #5b6775; font-size: 0.9rem; }
    .stButton > button { min-height: 2.7rem; }
    </style>
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    """,
    unsafe_allow_html=True,
)


def _init_state() -> None:
    if "progress" not in st.session_state:
        st.session_state.progress = load_progress()
    if "sheet" not in st.session_state:
        st.session_state.sheet = load_excel()
    if "quiz" not in st.session_state:
        st.session_state.quiz = []
        st.session_state.q_idx = 0
        st.session_state.q_done = False
        st.session_state.last_result = None
    if "card_idx" not in st.session_state:
        st.session_state.card_idx = 0
        st.session_state.show_answer = False
    st.session_state.setdefault("nav", "章から学ぶ")
    st.session_state.setdefault("chapter", None)
    st.session_state.setdefault("quiz_n", 5)
    st.session_state.setdefault("quiz_chapter", None)
    st.session_state.setdefault("quiz_field", None)
    st.session_state.setdefault("quiz_terms", None)
    st.session_state.setdefault("mode", None)
    st.session_state.setdefault("session_answered", 0)
    st.session_state.setdefault("session_correct", 0)
    st.session_state.setdefault("session_recorded", False)


def persist_sheet(df: pd.DataFrame) -> None:
    st.session_state.sheet = df
    save_both(df)


def persist_progress() -> None:
    save_progress(st.session_state.progress)


def chapter_count(chapter: str) -> int:
    return len(filter_terms(chapter=chapter))


def start_quiz(n: int, chapter: str | None = None, field: str | None = None, terms: list[str] | None = None) -> None:
    st.session_state.quiz_n = n
    st.session_state.quiz_chapter = chapter
    st.session_state.quiz_field = field
    st.session_state.quiz_terms = terms
    st.session_state.quiz = make_quiz(n=n, chapter=chapter, field=field, terms=terms)
    st.session_state.q_idx = 0
    st.session_state.q_done = False
    st.session_state.last_result = None
    st.session_state.nav = "クイズ"
    st.session_state.mode = "quiz"
    st.session_state.session_answered = 0
    st.session_state.session_correct = 0
    st.session_state.session_recorded = False


def start_cards(chapter: str) -> None:
    st.session_state.chapter = chapter
    st.session_state.card_idx = 0
    st.session_state.show_answer = False
    st.session_state.nav = "用語カード"
    st.session_state.mode = "cards"


def nav_bar() -> str:
    options = ["章から学ぶ", "用語カード", "クイズ", "弱点", "履歴", "試験情報"]
    current = st.session_state.nav if st.session_state.nav in options else "章から学ぶ"
    picked = st.radio("メニュー", options, index=options.index(current), horizontal=True, label_visibility="collapsed")
    st.session_state.nav = picked
    return picked


def page_chapters() -> None:
    st.title("G検定 スキマ学習")
    st.caption("公式シラバスの章から、今の隙間時間で解ける問数を選んでください。")

    p = st.session_state.progress
    answered = p["quiz"].get("answered", 0)
    correct = p["quiz"].get("correct", 0)
    rate = f"{(correct / answered * 100):.0f}%" if answered else "—"
    m1, m2, m3 = st.columns(3)
    m1.metric("正答率", rate)
    m2.metric("弱点", f"{len(st.session_state.sheet)}件")
    m3.metric("用語", f"{len(all_terms())}")
    stats_map = {r["章"]: r for r in chapter_stats(st.session_state.progress)}

    st.subheader("弱点だけ解く")
    weak_terms = [str(x) for x in st.session_state.sheet["用語"].tolist() if str(x)]
    unknown = list(st.session_state.progress.get("unknown", []))
    review_pool = list(dict.fromkeys(weak_terms + unknown))
    if review_pool:
        cols = st.columns(len(QUIZ_PRESETS))
        for col, preset in zip(cols, QUIZ_PRESETS):
            n = min(preset["n"], len(review_pool))
            if col.button(f"{preset['label']}\n{preset['hint']}", width="stretch", key=f"weak_{preset['n']}"):
                start_quiz(n, terms=review_pool)
                st.rerun()
    else:
        st.caption("まだ弱点がありません。章クイズで間違えるとここに溜まります。")

    for field, chapters_map in SYLLABUS_TREE.items():
        st.subheader(field)
        for chapter, sections in chapters_map.items():
            count = chapter_count(chapter)
            if count == 0:
                continue
            with st.container(border=True):
                ch_stat = stats_map.get(chapter, {})
                done = ch_stat.get("クイズ解答", 0)
                rate = ch_stat.get("正答率")
                extra = f"　解答{done}" + (f"　正答率{rate}%" if rate is not None else "")
                st.markdown(f"**{chapter}**　`{count}語`{extra}")
                st.caption(" / ".join(sections[:4]) + (" …" if len(sections) > 4 else ""))
                bcols = st.columns(len(QUIZ_PRESETS) + 1)
                if bcols[0].button("カード", width="stretch", key=f"card_{chapter}"):
                    start_cards(chapter)
                    st.rerun()
                for col, preset in zip(bcols[1:], QUIZ_PRESETS):
                    n = min(preset["n"], count)
                    if col.button(f"{preset['label']}", width="stretch", key=f"q_{chapter}_{preset['n']}"):
                        start_quiz(n, chapter=chapter, field=field)
                        st.rerun()


def page_cards() -> None:
    st.title("用語カード")
    chapter_names = [c for chapters_map in SYLLABUS_TREE.values() for c in chapters_map]
    current = st.session_state.chapter if st.session_state.chapter in chapter_names else chapter_names[0]
    chapter = st.selectbox("章", chapter_names, index=chapter_names.index(current))
    if chapter != st.session_state.chapter:
        st.session_state.chapter = chapter
        st.session_state.card_idx = 0
        st.session_state.show_answer = False

    only_unknown = st.checkbox("要復習だけ")
    items = filter_terms(chapter=chapter)
    unknown = set(st.session_state.progress.get("unknown", []))
    if only_unknown:
        items = [t for t in items if t["term"] in unknown]
    if not items:
        st.warning("この条件の用語がありません。")
        return

    if st.session_state.card_idx >= len(items):
        st.session_state.card_idx = 0
    item = items[st.session_state.card_idx]
    st.caption(f"{st.session_state.card_idx + 1} / {len(items)}　・　{item['section']}")
    st.markdown(
        f"<div class='term-card'><h2 style='margin:0 0 .4rem'>{item['term']}</h2>"
        f"<p class='muted'>{item['field']}</p></div>",
        unsafe_allow_html=True,
    )

    if st.button("定義を表示 / 隠す", type="primary", width="stretch"):
        st.session_state.show_answer = not st.session_state.show_answer
    if st.session_state.show_answer:
        st.info(item["definition"])
        st.write(f"**試験ポイント**　{item['exam_point']}")

    c1, c2, c3 = st.columns(3)
    if c1.button("← 前", width="stretch") and st.session_state.card_idx > 0:
        st.session_state.card_idx -= 1
        st.session_state.show_answer = False
        st.rerun()
    if c2.button("要復習", width="stretch"):
        st.session_state.progress = record_card(
            st.session_state.progress, item["term"], False, item["chapter"], item["field"]
        )
        persist_progress()
        if not already_has(st.session_state.sheet, item["term"]):
            persist_sheet(
                add_entry(
                    st.session_state.sheet,
                    {
                        "用語": item["term"],
                        "定義": item["definition"],
                        "試験ポイント": item["exam_point"],
                        "分野": item["field"],
                        "章": item["chapter"],
                        "節": item["section"],
                        "メモ": "カードで要復習",
                        "復習フラグ": "要復習",
                    },
                )
            )
        st.rerun()
    if c3.button("次へ →", width="stretch"):
        st.session_state.progress = record_card(
            st.session_state.progress, item["term"], True, item["chapter"], item["field"]
        )
        persist_progress()
        st.session_state.card_idx = min(st.session_state.card_idx + 1, len(items) - 1)
        st.session_state.show_answer = False
        st.rerun()

    st.divider()
    st.caption("この章をクイズで確認")
    qcols = st.columns(len(QUIZ_PRESETS))
    for col, preset in zip(qcols, QUIZ_PRESETS):
        n = min(preset["n"], len(items))
        if col.button(f"{preset['label']}\n{preset['hint']}", width="stretch", key=f"cardquiz_{preset['n']}"):
            start_quiz(n, chapter=chapter)
            st.rerun()


def page_quiz() -> None:
    st.title("用語クイズ")
    if not st.session_state.quiz:
        st.caption("章と問題数を選ぶと、すぐ始まります。")
        chapter_names = ["すべて"] + [c for chapters_map in SYLLABUS_TREE.values() for c in chapters_map]
        chapter = st.selectbox("章", chapter_names)
        cols = st.columns(len(QUIZ_PRESETS))
        for col, preset in zip(cols, QUIZ_PRESETS):
            if col.button(f"{preset['label']}\n{preset['hint']}", type="primary", width="stretch", key=f"solo_{preset['n']}"):
                ch = None if chapter == "すべて" else chapter
                start_quiz(preset["n"], chapter=ch)
                st.rerun()
        return

    quiz = st.session_state.quiz
    idx = st.session_state.q_idx
    total = len(quiz)
    where = st.session_state.quiz_chapter or "全範囲"
    st.caption(f"{where}　／　{total}問")
    st.progress(1.0 if st.session_state.q_done else idx / total, text=f"{min(idx + 1, total)} / {total}")

    if st.session_state.q_done:
        if not st.session_state.session_recorded:
            st.session_state.progress = record_session(
                st.session_state.progress,
                st.session_state.quiz_chapter,
                st.session_state.quiz_n,
                st.session_state.session_answered,
                st.session_state.session_correct,
            )
            persist_progress()
            st.session_state.session_recorded = True
        hist = st.session_state.progress["quiz"]
        sess_a = st.session_state.session_answered
        sess_c = st.session_state.session_correct
        if sess_a:
            st.success(f"今回 {sess_c} / {sess_a} 問正解　／　通算 {hist['correct']} / {hist['answered']}")
        else:
            st.success(f"終了。通算 {hist['correct']} / {hist['answered']} 問正解")
        if st.button("履歴を見る", width="stretch"):
            st.session_state.nav = "履歴"
            st.rerun()
        again = st.columns(len(QUIZ_PRESETS))
        for col, preset in zip(again, QUIZ_PRESETS):
            if col.button(f"もう{preset['label']}", width="stretch", key=f"again_{preset['n']}"):
                start_quiz(
                    preset["n"],
                    chapter=st.session_state.quiz_chapter,
                    field=st.session_state.quiz_field,
                    terms=st.session_state.quiz_terms,
                )
                st.rerun()
        if st.button("章一覧へ", width="stretch"):
            st.session_state.quiz = []
            st.session_state.nav = "章から学ぶ"
            st.rerun()
        return

    q = quiz[idx]
    st.subheader(f"Q{idx + 1}")
    st.write(q["stem"])
    choice = st.radio("選択肢", q["options"], key=f"choice_{idx}_{q['term']}")

    if st.session_state.last_result is None:
        if st.button("解答する", type="primary", width="stretch"):
            ok = choice == q["answer"]
            st.session_state.last_result = {"ok": ok, "choice": choice}
            st.session_state.progress = record_quiz(
                st.session_state.progress,
                ok,
                q["term"],
                chapter=q.get("chapter", ""),
                field=q.get("field", ""),
                section=q.get("section", ""),
            )
            st.session_state.session_answered += 1
            if ok:
                st.session_state.session_correct += 1
            persist_progress()
            if not ok:
                st.session_state.progress = record_card(
                    st.session_state.progress, q["term"], False, q.get("chapter", ""), q.get("field", "")
                )
                persist_progress()
            st.rerun()
        return

    result = st.session_state.last_result
    if result["ok"]:
        st.success(f"正解　{q['answer']}")
    else:
        st.error(f"不正解　あなたの解答: {result['choice']}")
        st.info(f"正解: {q['answer']}\n\n{q['definition']}")
        st.caption(q["exam_point"])
        if already_has(st.session_state.sheet, q["term"], q["stem"]):
            st.caption("この問題はすでに弱点ノートにあります。")
        elif st.button("弱点ノートに追加", type="primary", width="stretch"):
            persist_sheet(
                add_entry(
                    st.session_state.sheet,
                    {
                        "用語": q["term"],
                        "定義": q["definition"],
                        "試験ポイント": q["exam_point"],
                        "分野": q["field"],
                        "章": q["chapter"],
                        "節": q["section"],
                        "問題文": q["stem"],
                        "自分の解答": result["choice"],
                        "正解": q["answer"],
                        "メモ": "クイズで不正解",
                        "復習フラグ": "要復習",
                    },
                )
            )
            st.success("追加しました。弱点タブからExcel/Wordを保存できます。")

    if st.button("次の問題へ", width="stretch"):
        st.session_state.last_result = None
        if idx + 1 >= total:
            st.session_state.q_done = True
        else:
            st.session_state.q_idx += 1
        st.rerun()


def page_history() -> None:
    st.title("学習履歴")
    p = st.session_state.progress
    quiz = p.get("quiz", {})
    answered = int(quiz.get("answered", 0))
    correct = int(quiz.get("correct", 0))
    sessions = p.get("sessions", [])
    known_n = len(p.get("known", []))
    unknown_n = len(p.get("unknown", []))
    rate = f"{(correct / answered * 100):.0f}%" if answered else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("通算正答率", rate)
    c2.metric("解答数", answered)
    c3.metric("実施セット", len(sessions))
    c4.metric("要復習", unknown_n)

    if p.get("updated"):
        st.caption(f"最終更新: {p['updated']}　／　カード既知 {known_n}語")
    if is_cloud():
        st.info("公開版は再起動で消えることがあります。下のJSONを保存しておくと、学習履歴を戻せます。")

    daily = daily_quiz_counts(p)
    if daily:
        st.subheader("日別の解答数")
        st.bar_chart(pd.Series(daily, name="解答数"), width="stretch")

    if sessions:
        st.subheader("最近のクイズ")
        sess_df = pd.DataFrame(list(reversed(sessions[-30:])))
        sess_df = sess_df.rename(
            columns={"at": "日時", "chapter": "章", "n": "出題", "answered": "解答", "correct": "正解"}
        )
        if "正解" in sess_df.columns and "解答" in sess_df.columns:
            sess_df["正答率"] = [
                f"{round(100 * c / a)}%" if a else "—" for c, a in zip(sess_df["正解"], sess_df["解答"])
            ]
        st.dataframe(sess_df, hide_index=True, width="stretch")

    st.subheader("章ごとの進み")
    ch_df = pd.DataFrame(chapter_stats(p))
    if not ch_df.empty:
        show = ch_df.copy()
        show["正答率"] = show["正答率"].map(lambda x: f"{x}%" if x is not None else "—")
        st.dataframe(show, hide_index=True, width="stretch")

    weak = weak_terms_from_history(p)
    if weak:
        st.subheader("よく間違える用語")
        st.dataframe(pd.DataFrame(weak), hide_index=True, width="stretch")
        terms = [row["用語"] for row in weak]
        if st.button("この弱点だけ3問", width="stretch"):
            start_quiz(min(3, len(terms)), terms=terms)
            st.rerun()

    hist_rows = list(reversed(quiz.get("history", [])[-80:]))
    if hist_rows:
        st.subheader("直近の解答")
        qdf = pd.DataFrame(hist_rows)
        if "correct" in qdf.columns:
            qdf["結果"] = ["○" if bool(x) else "×" for x in qdf["correct"]]
        keep = [c for c in ["at", "結果", "term", "chapter"] if c in qdf.columns]
        qdf = qdf[keep].rename(columns={"at": "日時", "term": "用語", "chapter": "章"})
        st.dataframe(qdf, hide_index=True, width="stretch")
    elif not answered:
        st.caption("まだ履歴がありません。章クイズかカードを進めると、ここに溜まります。")

    st.subheader("履歴の保存")
    u1, u2 = st.columns(2)
    u1.download_button(
        "履歴JSONを保存",
        data=progress_bytes(p),
        file_name="G検定_学習履歴.json",
        mime="application/json",
        width="stretch",
    )
    uploaded = u2.file_uploader("履歴JSONを読み込む", type=["json"])
    if uploaded is not None:
        marker = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("_hist_loaded") != marker:
            st.session_state.progress = load_progress_bytes(uploaded.getvalue())
            persist_progress()
            st.session_state._hist_loaded = marker
            st.success("学習履歴を読み込みました。")
            st.rerun()


def page_sheet() -> None:
    st.title("弱点ノート")
    if is_cloud():
        st.info("公開版ではブラウザを閉じると消えることがあります。外出先で追加したら、下のボタンでExcelかWordを保存してください。")
    else:
        st.caption("自宅PCでは `data` フォルダにも保存します。スマホではダウンロードしてください。")

    uploaded = st.file_uploader("以前のExcelを読み込む", type=["xlsx"])
    if uploaded is not None:
        st.session_state.sheet = load_excel_bytes(uploaded.getvalue())
        save_both(st.session_state.sheet)
        st.success(f"{len(st.session_state.sheet)}件を読み込みました。")

    df = st.session_state.sheet
    st.metric("件数", len(df))
    if not df.empty:
        show_cols = [c for c in ["章", "用語", "定義", "自分の解答", "正解", "復習フラグ"] if c in df.columns]
        st.dataframe(df[show_cols], hide_index=True, width="stretch")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Excelを保存",
        data=excel_bytes(df),
        file_name="G検定_弱点チートシート.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    d2.download_button(
        "Wordを保存",
        data=word_bytes(df),
        file_name="G検定_弱点チートシート.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        width="stretch",
    )

    if review := [str(x) for x in df["用語"].tolist() if str(x)]:
        st.subheader("弱点をクイズにする")
        cols = st.columns(len(QUIZ_PRESETS))
        for col, preset in zip(cols, QUIZ_PRESETS):
            n = min(preset["n"], len(review))
            if col.button(f"{preset['label']}", width="stretch", key=f"sheetq_{preset['n']}"):
                start_quiz(n, terms=review)
                st.rerun()


def page_exam() -> None:
    st.title("試験情報")
    st.caption(f"出典: [JDLA公式]({OFFICIAL_URL})")
    st.write(f"**{EXAM_OVERVIEW['name']}**　{EXAM_OVERVIEW['purpose']}")
    st.info(
        f"**次回** {NEXT_ONLINE['回']}\n\n"
        f"{NEXT_ONLINE['日程']}\n\n"
        f"個人申込: {NEXT_ONLINE['個人申込']}\n\n"
        f"{NEXT_ONLINE['時間']} / {NEXT_ONLINE['出題数']}"
    )
    st.warning(NEXT_ONSITE_NOTE)
    st.markdown(f"[チケット購入]({TICKET_URL})　／　[シラバス]({SYLLABUS_URL})")
    st.write(f"一般 {FEES['一般']}　／　学生 {FEES['学生']}")
    with st.expander("2026年の注意"):
        for note in NOTES_2026:
            st.markdown(f"- {note}")
    with st.expander("年間スケジュール"):
        st.dataframe(pd.DataFrame(SCHEDULE_2026), hide_index=True, width="stretch")


def main() -> None:
    _init_state()
    page = nav_bar()
    if page == "章から学ぶ":
        page_chapters()
    elif page == "用語カード":
        page_cards()
    elif page == "クイズ":
        page_quiz()
    elif page == "弱点":
        page_sheet()
    elif page == "履歴":
        page_history()
    else:
        page_exam()


if __name__ == "__main__":
    main()

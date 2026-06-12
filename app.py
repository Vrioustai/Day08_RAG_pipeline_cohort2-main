"""
RAG Chatbot — Pháp luật ma tuý & Tin tức nghệ sĩ
Tab 1: Chatbot  |  Tab 2: Evaluation Dashboard
"""

import sys
import json
import os
from pathlib import Path

_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Trợ lý Pháp luật Ma tuý",
    page_icon="⚖️",
    layout="wide",
)

# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
.src-pill {
    display: inline-block;
    background: #f0f0f0;
    color: #555;
    font-size: 0.76rem;
    padding: 2px 9px;
    border-radius: 12px;
    margin: 2px 3px;
    border: 1px solid #ddd;
}
.src-box {
    margin-top: 8px;
    padding: 8px 12px;
    background: #fafafa;
    border-left: 3px solid #888;
    border-radius: 0 6px 6px 0;
    font-size: 0.82rem;
    color: #555;
}
/* Metric card */
.metric-card {
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-label { font-size: 0.82rem; color: #888; margin-bottom: 4px; }
.metric-val   { font-size: 2rem; font-weight: 700; }
.metric-sub   { font-size: 0.8rem; color: #aaa; }
.badge-a { color: #2e7d32; }
.badge-b { color: #1565c0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
TOPIC_KEYWORDS = [
    "ma tuý", "ma tuy", "ma túy", "chất cấm", "nghiện", "cai nghiện",
    "hình phạt", "xử phạt", "bị bắt", "khởi tố", "tạm giam", "tội",
    "luật", "pháp luật", "nghị định", "bộ luật", "điều", "khoản",
    "tàng trữ", "buôn bán", "vận chuyển", "sản xuất", "sử dụng",
    "nghệ sĩ", "ca sĩ", "rapper", "người mẫu", "diễn viên",
    "heroin", "cocaine", "cần sa", "amphetamine", "tiền chất",
    "phòng chống", "kiểm soát", "xử lý",
]

def is_on_topic(q: str) -> bool:
    return any(kw in q.lower() for kw in TOPIC_KEYWORDS)

@st.cache_resource(show_spinner="Đang khởi tạo pipeline...")
def load_pipeline():
    from task10_generation import generate_with_citation
    return generate_with_citation

# ─────────────────────────────────────────────
# LOAD EVAL RESULTS
# ─────────────────────────────────────────────
RESULTS_RAW = Path(__file__).parent / "group_project" / "evaluation" / "results_raw.json"
GOLDEN_PATH  = Path(__file__).parent / "group_project" / "evaluation" / "golden_dataset.json"

@st.cache_data
def load_eval_results():
    if not RESULTS_RAW.exists():
        return None, None
    data = json.loads(RESULTS_RAW.read_text(encoding="utf-8"))
    return data.get("config_a"), data.get("config_b")

@st.cache_data
def load_golden():
    if not GOLDEN_PATH.exists():
        return []
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


# ═════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════
tab_chat, tab_eval = st.tabs(["💬 Chatbot", "📊 Evaluation"])


# ─────────────────────────────────────────────
# TAB 1: CHATBOT
# ─────────────────────────────────────────────
with tab_chat:
    col_main, col_side = st.columns([3, 1])

    with col_side:
        st.markdown("### ⚖️ Trợ lý Pháp luật")
        st.caption("RAG · Hybrid Search · Citation")
        st.divider()
        st.markdown("**📚 Nguồn dữ liệu**")
        st.markdown("""
- Luật Phòng chống ma tuý 2021
- Bộ luật Hình sự – Chương XX
- Nghị định 57/2022/NĐ-CP
- Báo VnExpress (5 bài)
""")
        st.divider()
        st.markdown("**🔧 Pipeline**")
        st.code("Semantic\n+ BM25\n→ RRF\n→ Jina\n→ GPT-4o", language=None)
        st.divider()
        st.markdown("**🔑 API Keys (User)**")
        # Allow users to input API keys at runtime (stored in session only)
        openai_key_input = st.text_input("OpenAI API key (optional)", value=st.session_state.get("openai_key", ""), type="password")
        jina_key_input = st.text_input("Jina API key (optional)", value=st.session_state.get("jina_key", ""), type="password")
        if st.button("Apply API keys", use_container_width=True):
            if openai_key_input:
                os.environ["OPENAI_API_KEY"] = openai_key_input
                st.session_state["openai_key"] = openai_key_input
            if jina_key_input:
                os.environ["JINA_API_KEY"] = jina_key_input
                st.session_state["jina_key"] = jina_key_input
            st.success("API keys applied for this session")
        if st.button("🗑️ Xoá lịch sử", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    with col_main:
        st.title("⚖️ Trợ lý Pháp luật Ma tuý")
        st.caption("Hỏi về pháp luật, hình phạt, nghệ sĩ liên quan ma tuý · Có trích dẫn nguồn")

        with st.expander("💡 Câu hỏi gợi ý", expanded=False):
            q1, q2, q3 = st.columns(3)
            if q1.button("Hình phạt tội tàng trữ?", use_container_width=True):
                st.session_state._quick = "Hình phạt cho tội tàng trữ trái phép chất ma tuý?"
            if q2.button("Nghệ sĩ nào bị bắt?", use_container_width=True):
                st.session_state._quick = "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?"
            if q3.button("Quy trình cai nghiện?", use_container_width=True):
                st.session_state._quick = "Quy trình cai nghiện bắt buộc theo luật 2021?"

        st.divider()

        # Chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "⚖️"):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    src_names = list({s.get("metadata", {}).get("source", "?") for s in msg["sources"]})
                    pills = "".join(f'<span class="src-pill">📄 {s}</span>' for s in src_names[:6])
                    st.markdown(f'<div class="src-box">📎 <strong>Nguồn:</strong> {pills}</div>', unsafe_allow_html=True)

        # Input
        quick = st.session_state.pop("_quick", None)
        user_input = st.chat_input("Nhập câu hỏi về pháp luật ma tuý...") or quick

        if user_input:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(user_input)
            st.session_state.messages.append({"role": "user", "content": user_input, "sources": []})

            if not is_on_topic(user_input):
                off = ("Xin lỗi, tôi chỉ trả lời các câu hỏi về **pháp luật ma tuý**, "
                       "**hình phạt**, **cai nghiện**, hoặc **tin tức nghệ sĩ liên quan ma tuý**. 😊")
                with st.chat_message("assistant", avatar="⚖️"):
                    st.markdown(off)
                st.session_state.messages.append({"role": "assistant", "content": off, "sources": []})
                st.stop()

            with st.chat_message("assistant", avatar="⚖️"):
                with st.spinner("Đang tìm kiếm..."):
                    try:
                        # Ensure any user-provided API keys in session are applied to environment
                        if st.session_state.get("openai_key"):
                            os.environ["OPENAI_API_KEY"] = st.session_state.get("openai_key")
                        if st.session_state.get("jina_key"):
                            os.environ["JINA_API_KEY"] = st.session_state.get("jina_key")

                        result = load_pipeline()(user_input)
                        answer, sources = result["answer"], result["sources"]
                    except Exception as e:
                        answer, sources = f"Lỗi: `{e}`", []
                st.markdown(answer)
                if sources:
                    src_names = list({s.get("metadata", {}).get("source", "?") for s in sources})
                    pills = "".join(f'<span class="src-pill">📄 {s}</span>' for s in src_names[:6])
                    st.markdown(f'<div class="src-box">📎 <strong>Nguồn:</strong> {pills}</div>', unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})


# ─────────────────────────────────────────────
# TAB 2: EVALUATION DASHBOARD
# ─────────────────────────────────────────────
with tab_eval:
    st.title("📊 RAG Evaluation Dashboard")
    st.caption("Framework: RAGAS-style · LLM-as-judge (GPT-4o-mini) · 17 câu hỏi golden dataset")
    st.divider()

    res_a, res_b = load_eval_results()

    if res_a is None:
        st.warning("Chưa có kết quả evaluation. Chạy: `python group_project/evaluation/eval_pipeline.py`")
    else:
        import pandas as pd

        df_a = pd.DataFrame(res_a)
        df_b = pd.DataFrame(res_b) if res_b else None

        METRICS = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
        METRIC_LABELS = {
            "faithfulness":      "Faithfulness",
            "answer_relevancy":  "Answer Relevancy",
            "context_recall":    "Context Recall",
            "context_precision": "Context Precision",
        }

        # ── OVERVIEW SCORES ───────────────────────────────────────
        st.subheader("🏆 Tổng quan điểm số")

        avg_a = {m: round(df_a[m].mean(), 4) for m in METRICS if m in df_a}
        avg_b = {m: round(df_b[m].mean(), 4) for m in METRICS if m in df_b} if df_b is not None else {}
        overall_a = round(sum(avg_a.values()) / len(avg_a), 4)
        overall_b = round(sum(avg_b.values()) / len(avg_b), 4) if avg_b else None

        # Overall big metric
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Config A — Overall", f"{overall_a:.4f}",
                      help="Hybrid Search + Jina Reranking")
        with c2:
            if overall_b:
                delta = round(overall_a - overall_b, 4)
                st.metric("Config B — Overall", f"{overall_b:.4f}",
                          delta=f"{delta:+.4f} vs B",
                          help="Dense-only (Semantic Search)")
        with c3:
            golden = load_golden()
            st.metric("Golden Dataset", f"{len(golden)} câu hỏi",
                      help="legal / news / mixed")

        st.divider()

        # ── A/B COMPARISON BAR CHART ──────────────────────────────
        st.subheader("📈 So sánh A/B theo từng Metric")

        compare_data = []
        for m in METRICS:
            row = {"Metric": METRIC_LABELS[m]}
            if m in avg_a:
                row["Config A (Hybrid+Rerank)"] = avg_a[m]
            if avg_b and m in avg_b:
                row["Config B (Dense-only)"] = avg_b[m]
            compare_data.append(row)

        df_compare = pd.DataFrame(compare_data).set_index("Metric")
        st.bar_chart(df_compare, height=300)

        # ── A/B TABLE ─────────────────────────────────────────────
        st.subheader("📋 Bảng so sánh chi tiết")
        cols = st.columns(len(METRICS))
        for col, m in zip(cols, METRICS):
            a_val = avg_a.get(m, 0)
            b_val = avg_b.get(m, 0) if avg_b else None
            delta_str = f"{a_val - b_val:+.4f}" if b_val is not None else "—"
            color = "normal" if b_val is None else ("inverse" if a_val < b_val else "normal")
            col.metric(
                label=METRIC_LABELS[m],
                value=f"{a_val:.4f}",
                delta=delta_str if b_val is not None else None,
                delta_color=color,
            )

        st.divider()

        # ── PER-QUESTION DETAIL ───────────────────────────────────
        st.subheader("🔍 Chi tiết theo từng câu hỏi")

        # Merge golden questions
        golden = load_golden()
        qmap = {g["id"]: g for g in golden}

        detail_rows = []
        for r in res_a:
            qid = r.get("id", "?")
            q_info = qmap.get(qid, {})
            detail_rows.append({
                "ID": qid,
                "Category": q_info.get("category", r.get("category", "?")),
                "Câu hỏi": q_info.get("question", r.get("question", ""))[:65] + "...",
                "Faithfulness": r.get("faithfulness", 0),
                "Ans Relevancy": r.get("answer_relevancy", 0),
                "Ctx Recall":    r.get("context_recall", 0),
                "Ctx Precision": r.get("context_precision", 0),
            })

        df_detail = pd.DataFrame(detail_rows)

        # Color map
        def color_score(val):
            if isinstance(val, float):
                if val >= 0.9:   return "background-color: #c8e6c9"
                elif val >= 0.7: return "background-color: #fff9c4"
                else:            return "background-color: #ffcdd2"
            return ""

        score_cols = ["Faithfulness", "Ans Relevancy", "Ctx Recall", "Ctx Precision"]
        styled = df_detail.style.map(color_score, subset=score_cols).format(
            {c: "{:.2f}" for c in score_cols}
        )
        st.dataframe(styled, use_container_width=True, height=460)

        st.divider()

        # ── WORST PERFORMERS ─────────────────────────────────────
        st.subheader("⚠️ Worst Performers (Faithfulness thấp nhất)")
        worst = df_detail.nsmallest(3, "Faithfulness")[["ID", "Category", "Câu hỏi", "Faithfulness", "Ans Relevancy"]]
        st.dataframe(worst, use_container_width=True, hide_index=True)

        st.divider()

        # ── CATEGORY BREAKDOWN ────────────────────────────────────
        st.subheader("📂 Điểm trung bình theo Category")
        df_cat = df_detail.groupby("Category")[score_cols].mean().round(4)
        st.dataframe(df_cat.style.map(color_score).format("{:.4f}"), use_container_width=True)

        st.divider()

        # ── ANALYSIS ─────────────────────────────────────────────
        st.subheader("💡 Phân tích & Đề xuất cải tiến")
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("""
**Nhận xét:**
- ✅ **Answer Relevancy = 0.98** — GPT-4o-mini hiểu câu hỏi rất tốt
- ✅ **Faithfulness = 0.85** — LLM bám sát nguồn, ít hallucinate  
- ⚠️ **Context Recall = 0.75** — Corpus còn thiếu văn bản pháp luật chi tiết
- ℹ️ Câu hỏi về tin tức nghệ sĩ đạt điểm cao hơn câu hỏi pháp luật
""")
        with col_r:
            st.markdown("""
**Đề xuất cải tiến:**
1. 📄 **Thêm dữ liệu** — Bộ luật Hình sự đầy đủ, Nghị định 105/2021
2. ✂️ **Better chunking** — Chunk theo điều khoản luật  
3. 🔍 **Query expansion** — Thêm từ đồng nghĩa tiếng Việt cho BM25
4. 🎯 **Fine-tune reranker** — Jina Reranker trên văn bản pháp luật VN
5. 🕸️ **Knowledge graph** (giai đoạn 2) — Liên kết điều luật ↔ vụ án
""")

        st.caption("*Kết quả từ RAGAS Evaluation Pipeline — Day 8 Group Project*")

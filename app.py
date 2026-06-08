"""
RAG Chatbot — Pháp luật ma tuý & Tin tức nghệ sĩ
"""

import sys
import os
from pathlib import Path

_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Trợ lý Pháp luật Ma tuý",
    page_icon="⚖️",
    layout="centered",
)

# ─────────────────────────────────────────────
# MINIMAL CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* Source pill */
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
/* Source box */
.src-box {
    margin-top: 8px;
    padding: 8px 12px;
    background: #fafafa;
    border-left: 3px solid #888;
    border-radius: 0 6px 6px 0;
    font-size: 0.82rem;
    color: #555;
}
/* Off-topic box */
.off-topic {
    padding: 10px 14px;
    background: #fff8e1;
    border-left: 3px solid #ffc107;
    border-radius: 0 6px 6px 0;
    font-size: 0.9rem;
    color: #555;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []


# ─────────────────────────────────────────────
# TOPIC GUARD — kiểm tra câu hỏi có đúng chủ đề không
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

def is_on_topic(query: str) -> bool:
    """Trả về True nếu câu hỏi liên quan đến chủ đề."""
    q = query.lower()
    return any(kw in q for kw in TOPIC_KEYWORDS)


# ─────────────────────────────────────────────
# LOAD PIPELINE (lazy — chỉ load khi cần)
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="Đang khởi tạo pipeline...")
def load_pipeline():
    from task10_generation import generate_with_citation
    return generate_with_citation


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.title("⚖️ Trợ lý Pháp luật Ma tuý")
st.caption("Hỏi về pháp luật, hình phạt, nghệ sĩ liên quan ma tuý · Có trích dẫn nguồn")

# Quick questions
with st.expander("💡 Câu hỏi gợi ý", expanded=False):
    q1, q2, q3 = st.columns(3)
    if q1.button("Hình phạt tội tàng trữ?", use_container_width=True):
        st.session_state._quick = "Hình phạt cho tội tàng trữ trái phép chất ma tuý là bao nhiêu?"
    if q2.button("Nghệ sĩ nào bị bắt?", use_container_width=True):
        st.session_state._quick = "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?"
    if q3.button("Quy trình cai nghiện?", use_container_width=True):
        st.session_state._quick = "Quy trình cai nghiện bắt buộc theo luật 2021 là gì?"

st.divider()

# ─────────────────────────────────────────────
# HIỂN THỊ LỊCH SỬ CHAT
# ─────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "⚖️"):
        st.markdown(msg["content"])

        # Hiển thị sources nếu có
        if msg["role"] == "assistant" and msg.get("sources"):
            src_names = list({
                s.get("metadata", {}).get("source", "?")
                for s in msg["sources"]
            })
            pills = "".join(f'<span class="src-pill">📄 {s}</span>' for s in src_names[:6])
            st.markdown(
                f'<div class="src-box">📎 <strong>Nguồn:</strong> {pills}</div>',
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────────
quick = st.session_state.pop("_quick", None)
user_input = st.chat_input("Nhập câu hỏi về pháp luật ma tuý...") or quick

if user_input:
    # Hiển thị tin nhắn user
    with st.chat_message("user", avatar="🧑"):
        st.markdown(user_input)
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "sources": [],
    })

    # ── Kiểm tra chủ đề ──────────────────────────────────────────
    if not is_on_topic(user_input):
        off_msg = (
            "Xin lỗi, tôi chỉ có thể trả lời các câu hỏi liên quan đến "
            "**pháp luật ma tuý**, **hình phạt**, **cai nghiện**, hoặc "
            "**tin tức nghệ sĩ liên quan ma tuý**. "
            "Bạn có thể thử hỏi lại với chủ đề phù hợp hơn không? 😊"
        )
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(off_msg)
        st.session_state.messages.append({
            "role": "assistant",
            "content": off_msg,
            "sources": [],
        })
        st.stop()

    # ── Gọi pipeline ─────────────────────────────────────────────
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Đang tìm kiếm..."):
            try:
                generate = load_pipeline()
                result = generate(user_input)
                answer = result["answer"]
                sources = result["sources"]
            except Exception as e:
                answer = f"Xin lỗi, đã có lỗi xảy ra: `{e}`"
                sources = []

        st.markdown(answer)

        # Sources
        if sources:
            src_names = list({
                s.get("metadata", {}).get("source", "?")
                for s in sources
            })
            pills = "".join(f'<span class="src-pill">📄 {s}</span>' for s in src_names[:6])
            st.markdown(
                f'<div class="src-box">📎 <strong>Nguồn:</strong> {pills}</div>',
                unsafe_allow_html=True,
            )

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
    })


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚖️ Trợ lý Pháp luật Ma tuý")
    st.caption("RAG Pipeline · Hybrid Search · Citation")
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
    st.markdown("""
```
Query
 ├─ Semantic Search
 ├─ BM25 Search
 ├─ RRF Merge
 ├─ Jina Rerank
 └─ GPT-4o-mini
```
""")
    st.divider()

    if st.button("🗑️ Xoá lịch sử", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

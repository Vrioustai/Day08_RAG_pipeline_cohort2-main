"""
Task 10 — Generation Có Citation.

Hướng dẫn:
    1. Chọn top_k, top_p phù hợp (giải thích lý do)
    2. Sắp xếp lại chunks sau reranking để tránh "lost in the middle"
    3. Inject context vào prompt
    4. Yêu cầu LLM trả lời có citation
    5. Nếu không đủ evidence → "Tôi không thể xác minh thông tin này"
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Thêm src vào sys.path một lần duy nhất
_src_dir = str(Path(__file__).parent.resolve())
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from task9_retrieval_pipeline import retrieve  # noqa: E402


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn
# =============================================================================

# top_k = 5:
#   - Đủ evidence (2-3 nguồn pháp luật + 2 bài báo)
#   - Không quá dài gây "lost in the middle" (Liu et al. 2023)
#   - Context window ~2000 tokens, vừa đủ cho gpt-4o-mini
TOP_K = 5

# top_p = 0.9 (nucleus sampling):
#   - Giữ 90% xác suất tích luỹ → đủ đa dạng
#   - Không quá random (top_p=1.0) gây hallucination
#   - RAG factual cần trung dung giữa creativity và accuracy
TOP_P = 0.9

# temperature = 0.2:
#   - Gần 0 = factual, ít sáng tạo → phù hợp RAG pháp luật
#   - 0.2 thay vì 0.0 để tránh lặp từ và vẫn có ngôn ngữ tự nhiên
TEMPERATURE = 0.2

MODEL = "gpt-4o-mini"  # Nhanh, rẻ, đủ tốt cho RAG task


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """Bạn là trợ lý AI thân thiện, chuyên về pháp luật ma tuý Việt Nam.
Hãy trả lời tự nhiên, dễ hiểu bằng tiếng Việt, như đang giải thích cho người dùng bình thường.

Yêu cầu:
1. Trả lời tự nhiên, không quá cứng nhắc — như một người bạn am hiểu pháp luật đang giải thích
2. Với MỖI thông tin thực tế, chèn citation nhỏ gọn ngay sau, dạng [Nguồn] hoặc [Tên luật, Điều X]
   Ví dụ: "Tội tàng trữ ma tuý bị phạt tù từ 1–5 năm [BLHS 2015, Điều 249]"
3. CHỈ dùng thông tin từ tài liệu được cung cấp
4. Nếu không có đủ thông tin → nói thẳng "Tôi không tìm thấy thông tin này trong tài liệu hiện có"
5. Cuối câu trả lời thêm dòng "📎 Nguồn: ..." liệt kê ngắn gọn các tài liệu đã dùng
"""


# =============================================================================
# DOCUMENT REORDERING — tránh "lost in the middle"
# =============================================================================

def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """
    Sắp xếp chunks để tránh "lost in the middle" effect.

    LLM chú ý tốt nhất ở ĐẦU và CUỐI prompt, kém nhất ở GIỮA.
    (Liu et al. 2023 - "Lost in the Middle: How Language Models Use Long Contexts")

    Strategy: đặt chunks quan trọng nhất xen kẽ đầu-cuối, kém quan trọng ở giữa.

    Input (sorted by score desc): [rank1, rank2, rank3, rank4, rank5]
    Output:                        [rank1, rank3, rank5, rank4, rank2]
    → rank1 ở đầu (attention cao), rank2 ở cuối (attention cao), rank3,4,5 ở giữa

    Args:
        chunks: List sorted by score descending

    Returns:
        List reordered để maximize LLM attention cho chunks quan trọng.
    """
    if len(chunks) <= 2:
        return chunks

    # Tách thành 2 nhóm: chẵn → đầu, lẻ → cuối (reversed)
    front = chunks[::2]    # index 0, 2, 4 → đặt ở đầu
    back = chunks[1::2]    # index 1, 3    → đặt ở cuối (reversed)

    return front + back[::-1]


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================

def format_context(chunks: list[dict]) -> str:
    """
    Format chunks thành context string cho prompt.
    Mỗi chunk có label source để LLM có thể cite đúng.

    Args:
        chunks: List of {'content': str, 'metadata': dict, 'score': float}

    Returns:
        Formatted context string.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", f"Document {i}")
        doc_type = meta.get("type", "unknown")

        # Tạo citation label ngắn gọn
        if "73luat" in source:
            label = "Luật Phòng chống ma tuý 2021"
        elif "57-cp" in source:
            label = "Nghị định 57/2022/NĐ-CP"
        elif "cac-toi-pham" in source:
            label = "Bộ luật Hình sự 2015 (Chương XX)"
        elif "article" in source:
            label = f"VnExpress, 2024 ({source})"
        else:
            label = source

        context_parts.append(
            f"[Tài liệu {i} | Cite as: {label} | Loại: {doc_type}]\n"
            f"{chunk['content']}\n"
        )

    return "\n---\n".join(context_parts)


# =============================================================================
# GENERATION
# =============================================================================

def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """
    End-to-end RAG generation có citation.

    Pipeline:
        1. Retrieve relevant chunks (task 9)
        2. Reorder để tránh lost in the middle
        3. Format context với source labels
        4. Build prompt = SYSTEM_PROMPT + context + query
        5. Gọi OpenAI GPT-4o-mini
        6. Return answer + sources

    Args:
        query: Câu hỏi của user
        top_k: Số chunks đưa vào context

    Returns:
        {
            'answer': str,           # Câu trả lời có citation
            'sources': list[dict],   # Các chunks đã dùng
            'retrieval_source': str  # 'hybrid' hoặc 'pageindex'
        }
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Bước 1: Retrieve
    chunks = retrieve(query, top_k=top_k, use_pageindex_fallback=False)

    if not chunks:
        return {
            "answer": "Tôi không thể xác minh thông tin này từ nguồn hiện có.",
            "sources": [],
            "retrieval_source": "none",
        }

    # Bước 2: Reorder tránh lost in the middle
    reordered = reorder_for_llm(chunks)

    # Bước 3: Format context
    context = format_context(reordered)

    # Bước 4: Build prompt
    user_message = (
        f"Dưới đây là các tài liệu liên quan:\n\n"
        f"{context}\n\n"
        f"---\n\n"
        f"Câu hỏi: {query}"
    )

    # Bước 5: Gọi LLM
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )

    answer = response.choices[0].message.content
    retrieval_source = chunks[0].get("retrieval_source", "hybrid") if chunks else "none"

    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý theo pháp luật Việt Nam?",
        "Những nghệ sĩ nào đã bị bắt vì liên quan tới ma tuý?",
        "Quy trình cai nghiện bắt buộc theo Luật Phòng chống ma tuý 2021?",
    ]

    for q in test_queries:
        print(f"\n{'='*70}")
        print(f"Q: {q}")
        print("=" * 70)
        result = generate_with_citation(q)
        print(f"\nA:\n{result['answer']}")
        print(f"\n[{len(result['sources'])} chunks | via {result['retrieval_source']}]")

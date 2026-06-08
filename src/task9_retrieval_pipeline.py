"""
Task 9 — Retrieval Pipeline Hoàn Chỉnh.

Kết hợp semantic search + lexical search + reranking + PageIndex fallback
thành một pipeline thống nhất.

Logic:
    1. Chạy semantic_search + lexical_search song song
    2. Merge kết quả bằng RRF (Reciprocal Rank Fusion)
    3. Rerank (Jina cross-encoder nếu có key, fallback RRF)
    4. Nếu top result score < threshold → fallback sang PageIndex vectorless
    5. Return top_k results
"""

import sys
from pathlib import Path

# Thêm src vào sys.path để import được khi chạy trực tiếp
_src_dir = str(Path(__file__).parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from task5_semantic_search import semantic_search
from task6_lexical_search import lexical_search
from task7_reranking import rerank, rerank_rrf
from task8_pageindex_vectorless import pageindex_search


# =============================================================================
# CONFIGURATION
# =============================================================================

# RRF score thường rất nhỏ (~0.01-0.03), threshold này dùng cho Jina score (0-1)
# Nếu dùng RRF thuần thì threshold = 0 (luôn dùng hybrid, không fallback)
SCORE_THRESHOLD = 0.3   # Ngưỡng cho cross-encoder score; fallback PageIndex nếu thấp hơn
DEFAULT_TOP_K = 5
RERANK_METHOD = "auto"  # "auto" = Jina nếu có key, RRF nếu không


def retrieve(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    score_threshold: float = SCORE_THRESHOLD,
    use_reranking: bool = True,
    use_pageindex_fallback: bool = True,
) -> list[dict]:
    """
    Retrieval pipeline hoàn chỉnh với fallback logic.

    Pipeline:
        Query
          ├─→ Semantic Search (Task 5) ──┐
          │                              ├─→ RRF Merge → Rerank (Task 7) → Results
          ├─→ Lexical Search  (Task 6) ──┘
          │
          └─→ Nếu best_score < threshold:
                └─→ Fallback: PageIndex Vectorless (Task 8)

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả cuối cùng
        score_threshold: Ngưỡng điểm tối thiểu (áp dụng cho cross-encoder score)
        use_reranking: Có áp dụng reranking không
        use_pageindex_fallback: Có dùng PageIndex khi score thấp không

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'retrieval_source': str  # 'hybrid' hoặc 'pageindex'
        }
    """
    print(f"  [Pipeline] Query: {query[:60]}...")

    # ── Step 1: Chạy semantic + lexical search ───────────────────────────────
    print("  [1/4] Semantic search...")
    dense_results = semantic_search(query, top_k=top_k * 2)

    print("  [2/4] Lexical search (BM25)...")
    sparse_results = lexical_search(query, top_k=top_k * 2)

    print(f"        dense={len(dense_results)}, sparse={len(sparse_results)}")

    # ── Step 2: Merge bằng RRF ────────────────────────────────────────────────
    print("  [3/4] Merge bằng RRF...")
    merged = rerank_rrf([dense_results, sparse_results], top_k=top_k * 2)
    for item in merged:
        item["retrieval_source"] = "hybrid"

    # ── Step 3: Rerank ────────────────────────────────────────────────────────
    if use_reranking and merged:
        print(f"  [4/4] Rerank ({RERANK_METHOD})...")
        try:
            final_results = rerank(query, merged, top_k=top_k, method=RERANK_METHOD)
            for item in final_results:
                item["retrieval_source"] = "hybrid"
        except Exception as e:
            print(f"        ⚠ Rerank lỗi ({e}), dùng RRF results.")
            final_results = merged[:top_k]
    else:
        print("  [4/4] Bỏ qua rerank.")
        final_results = merged[:top_k]

    # ── Step 4: Kiểm tra threshold → fallback PageIndex ───────────────────────
    best_score = final_results[0]["score"] if final_results else 0.0

    if use_pageindex_fallback and (not final_results or best_score < score_threshold):
        print(f"  ⚠ Best score ({best_score:.4f}) < threshold ({score_threshold})")
        print("  → Fallback: PageIndex Vectorless...")
        try:
            fallback = pageindex_search(query, top_k=top_k)
            for item in fallback:
                item["retrieval_source"] = "pageindex"
            print(f"  ✓ PageIndex trả về {len(fallback)} kết quả")
            return fallback
        except Exception as e:
            print(f"  ⚠ PageIndex fallback thất bại: {e}")
            # Trả về hybrid dù score thấp

    print(f"  ✓ Hybrid pipeline: {len(final_results)} kết quả (best_score={best_score:.4f})")
    return final_results[:top_k]


if __name__ == "__main__":
    test_queries = [
        "Hình phạt cho tội tàng trữ trái phép chất ma tuý",
        "Ca sĩ nào bị bắt vì sử dụng ma tuý",
        "Luật phòng chống ma tuý 2021 quy định về cai nghiện",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print('='*60)
        results = retrieve(q, top_k=3, use_pageindex_fallback=False)
        print()
        for i, r in enumerate(results, 1):
            src = r.get("retrieval_source", "?")
            print(f"  {i}. [score={r['score']:.4f}] [{src}] source={r['metadata'].get('source')}")
            print(f"     {r['content'][:100]}...")

"""
Task 7 — Reranking Module.

Phương pháp chọn:
    1. Cross-encoder: Jina Reranker v2 (multilingual) qua API
       - Tốt cho tiếng Việt, không cần load model local (tránh torch hang trên Python 3.14)
       - Dùng khi có JINA_API_KEY

    2. RRF (Reciprocal Rank Fusion): tự implement, không cần API
       - Gộp kết quả từ semantic search + lexical search
       - Công thức: RRF(d) = Σ 1 / (k + rank_r(d))  với k=60 (Cormack et al. 2009)
       - Dùng làm fallback khi không có Jina API key

Cách dùng:
    - rerank(query, candidates) → dùng Jina nếu có key, fallback RRF
    - rerank_rrf([list1, list2]) → gộp 2 ranked lists bằng RRF
"""

import os
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# Cross-encoder: Jina Reranker API
# =============================================================================

def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates bằng Jina Reranker v2 (cross-encoder, multilingual).

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số lượng kết quả sau rerank

    Returns:
        List of top_k candidates, re-scored và sorted by rerank_score descending.
    """
    import requests

    jina_key = os.getenv("JINA_API_KEY", "")
    if not jina_key:
        raise ValueError("JINA_API_KEY chưa được set (vui lòng nhập trong UI hoặc env)")

    response = requests.post(
        "https://api.jina.ai/v1/rerank",
        headers={
            "Authorization": f"Bearer {jina_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": [c["content"] for c in candidates],
            "top_n": top_k,
        },
        timeout=30,
    )
    response.raise_for_status()

    reranked = response.json()["results"]
    results = []
    for r in reranked:
        item = candidates[r["index"]].copy()
        item["score"] = round(r["relevance_score"], 4)
        item["rerank_method"] = "jina_cross_encoder"
        results.append(item)

    return results


# =============================================================================
# RRF (Reciprocal Rank Fusion) — tự implement
# =============================================================================

def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    Công thức: RRF(d) = Σ 1 / (k + rank_r(d))
    - k=60: hằng số smoothing từ paper Cormack et al. 2009
    - rank_r(d): thứ hạng của document d trong ranker r (bắt đầu từ 1)

    Tại sao dùng RRF:
    - Không cần normalize score giữa các ranker (BM25 và cosine score khác đơn vị)
    - Document xuất hiện trong nhiều list + xếp hạng cao → điểm cao
    - Robust, ổn định hơn weighted sum

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số kết quả cuối cùng
        k: Smoothing constant (default=60)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    rrf_scores: dict[str, float] = {}   # content → RRF score
    content_map: dict[str, dict] = {}   # content → full dict

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item["content"]
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)
            content_map[key] = item

    # Sort theo RRF score giảm dần
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for content, score in sorted_items[:top_k]:
        item = content_map[content].copy()
        item["score"] = round(score, 6)
        item["rerank_method"] = "rrf"
        results.append(item)

    return results


# =============================================================================
# Unified rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "auto",
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query: Câu truy vấn
        candidates: Danh sách candidates từ retrieval
        top_k: Số lượng kết quả sau rerank
        method: "auto" | "cross_encoder" | "rrf"
                "auto" = dùng Jina nếu có key, fallback RRF

    Returns:
        List of top_k reranked candidates, sorted by score descending.
    """
    if method == "auto":
        method = "cross_encoder" if os.getenv("JINA_API_KEY") else "rrf"

    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "rrf":
        # RRF với 1 list = chỉ sort lại theo score gốc, lấy top_k
        return rerank_rrf([candidates], top_k=top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    # Test với data thực từ task 5 + task 6
    from task5_semantic_search import semantic_search
    from task6_lexical_search import lexical_search

    query = "hình phạt tội tàng trữ ma tuý"
    print(f"Query: {query}\n")

    # Lấy kết quả từ cả 2 search
    semantic_results = semantic_search(query, top_k=5)
    lexical_results = lexical_search(query, top_k=5)

    print("--- Trước rerank (semantic top 3) ---")
    for i, r in enumerate(semantic_results[:3], 1):
        print(f"  [{i}] score={r['score']:.4f} | {r['content'][:70]}...")

    # RRF gộp kết quả từ 2 nguồn
    print("\n--- Sau RRF (gộp semantic + lexical) ---")
    rrf_results = rerank_rrf([semantic_results, lexical_results], top_k=5)
    for i, r in enumerate(rrf_results, 1):
        print(f"  [{i}] rrf_score={r['score']:.6f} | source={r['metadata'].get('source')} | {r['content'][:70]}...")

    # Jina cross-encoder nếu có key
    if JINA_API_KEY:
        print("\n--- Sau Jina Cross-encoder ---")
        jina_results = rerank_cross_encoder(query, semantic_results, top_k=3)
        for i, r in enumerate(jina_results, 1):
            print(f"  [{i}] jina_score={r['score']:.4f} | {r['content'][:70]}...")
    else:
        print("\n(Không có JINA_API_KEY — bỏ qua test cross-encoder)")

"""
Task 6 — Lexical Search Module (BM25).

Mặc định sử dụng BM25. Nếu dùng phương pháp khác (TF-IDF, Elasticsearch,
Weaviate BM25 built-in), hãy giải thích cơ chế trong buổi demo → +5 bonus.

Cài đặt:
    pip install rank-bm25

BM25 hoạt động thế nào:
    - Term Frequency (TF): từ xuất hiện nhiều trong document → điểm cao
    - Inverse Document Frequency (IDF): từ hiếm → quan trọng hơn
    - Document length normalization: document dài không bị ưu tiên quá mức
    - Formula: score(q,d) = Σ IDF(qi) * (tf(qi,d) * (k1+1)) / (tf(qi,d) + k1*(1-b+b*|d|/avgdl))
    - k1=1.5 (term saturation), b=0.75 (length normalization)

Corpus: load từ ChromaDB (dùng chung với Task 4/5 — không cần đọc lại file)
Tokenize: dùng split() đơn giản cho tiếng Việt (không cần underthesea)
"""

from pathlib import Path

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "drug_law_docs"

# Cache để không build lại index mỗi lần gọi
_bm25 = None
_corpus: list[dict] = []


def _load_corpus_from_chroma() -> list[dict]:
    """Load toàn bộ chunks từ ChromaDB làm corpus cho BM25."""
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    # Lấy tất cả documents (không cần embedding)
    total = collection.count()
    result = collection.get(
        limit=total,
        include=["documents", "metadatas"],
    )

    corpus = []
    for doc, meta in zip(result["documents"], result["metadatas"]):
        corpus.append({
            "content": doc,
            "metadata": meta,
        })
    return corpus


def build_bm25_index(corpus: list[dict]):
    """
    Xây dựng BM25 index từ corpus.

    Args:
        corpus: List of {'content': str, 'metadata': dict}

    Returns:
        BM25Okapi object
    """
    from rank_bm25 import BM25Okapi

    # Tokenize: lowercase + split theo khoảng trắng
    # Phù hợp tiếng Việt vì từ tiếng Việt đã cách nhau bằng dấu cách
    tokenized_corpus = [doc["content"].lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25


def _get_bm25_and_corpus():
    """Load corpus và build BM25 index một lần, cache lại."""
    global _bm25, _corpus
    if _bm25 is None:
        _corpus = _load_corpus_from_chroma()
        _bm25 = build_bm25_index(_corpus)
    return _bm25, _corpus


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm từ khóa sử dụng BM25.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,
            'score': float,      # BM25 score (cao hơn = liên quan hơn)
            'metadata': dict     # source, type, chunk_index
        }
        Sorted by score descending.
    """
    import numpy as np

    bm25, corpus = _get_bm25_and_corpus()

    # Tokenize query giống cách tokenize corpus
    tokenized_query = query.lower().split()

    # Tính BM25 score cho tất cả documents
    scores = bm25.get_scores(tokenized_query)

    # Lấy top_k indices có score cao nhất
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Bỏ qua document không có từ khớp
            results.append({
                "content": corpus[idx]["content"],
                "score": round(float(scores[idx]), 4),
                "metadata": corpus[idx]["metadata"],
            })

    # Đã sorted sẵn theo score giảm dần
    return results


if __name__ == "__main__":
    print("=== Test Lexical Search (BM25) ===\n")

    queries = [
        "Điều 249 tàng trữ trái phép chất ma tuý",
        "ca sĩ bị bắt sử dụng ma túy",
        "mức phạt tù buôn bán",
    ]

    for q in queries:
        print(f"Query: {q}")
        results = lexical_search(q, top_k=3)
        if not results:
            print("  (Không có kết quả)")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] score={r['score']:.4f} | source={r['metadata'].get('source')} | {r['content'][:80]}...")
        print()

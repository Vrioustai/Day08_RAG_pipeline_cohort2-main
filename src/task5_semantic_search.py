"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Tương thích với embedding model và vector store ở Task 4

Embedding: OpenAI text-embedding-3-small (tránh sentence-transformers bị treo trên Python 3.14)
Vector store: ChromaDB local
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Cùng config với Task 4
EMBEDDING_MODEL = "text-embedding-3-small"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
COLLECTION_NAME = "drug_law_docs"

# Cache client để không khởi tạo lại mỗi lần gọi
_openai_client = None
_collection = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity (cosine).

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score (0-1, cao hơn = tốt hơn)
            'metadata': dict     # source, type, chunk_index
        }
        Sorted by score descending.
    """
    # Bước 1: Embed query bằng cùng model ở Task 4
    client = _get_openai_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
    )
    query_embedding = response.data[0].embedding

    # Bước 2: Query ChromaDB bằng cosine similarity
    collection = _get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # Bước 3: Format kết quả
    # ChromaDB trả distance (cosine distance: 0 = giống, 2 = khác)
    # Chuyển sang similarity: score = 1 - distance
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    output = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        output.append({
            "content": doc,
            "score": round(1 - dist, 4),
            "metadata": meta,
        })

    # Sắp xếp theo score giảm dần
    output.sort(key=lambda x: x["score"], reverse=True)
    return output


if __name__ == "__main__":
    print("=== Test Semantic Search ===\n")

    queries = [
        "hình phạt cho tội tàng trữ ma tuý",
        "ca sĩ bị bắt vì sử dụng ma túy",
        "mức xử phạt buôn bán chất cấm",
    ]

    for q in queries:
        print(f"Query: {q}")
        results = semantic_search(q, top_k=3)
        for i, r in enumerate(results, 1):
            print(f"  [{i}] score={r['score']:.4f} | source={r['metadata'].get('source')} | {r['content'][:80]}...")
        print()

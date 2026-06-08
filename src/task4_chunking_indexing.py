"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (ChromaDB — local, không cần server)

Chunking options (langchain-text-splitters):
    - RecursiveCharacterTextSplitter: an toàn, phổ biến
    - MarkdownHeaderTextSplitter: tốt cho file có heading
    - SemanticChunker: dùng embedding để tách (nâng cao)

Embedding model:
    - OpenAI text-embedding-3-small (1536 dim)
    - Lý do: sentence-transformers bị treo trên Python 3.14 do torch chưa hỗ trợ
    - OpenAI API ổn định, không cần load model local, tốt cho tiếng Việt

Vector store: ChromaDB (local, không cần Docker/server)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"

# =============================================================================
# CONFIGURATION
# =============================================================================

# RecursiveCharacterTextSplitter vì:
# - Tài liệu pháp luật và báo chí có cấu trúc đoạn văn rõ ràng
# - Splitter này ưu tiên tách theo \n\n (đoạn), rồi \n (dòng), rồi câu
# - An toàn nhất khi không biết trước cấu trúc file
CHUNK_SIZE = 500        # 500 ký tự ≈ 2-3 câu, đủ context mà không quá dài
CHUNK_OVERLAP = 50      # 50 ký tự overlap để không mất context giữa 2 chunk
CHUNKING_METHOD = "recursive"

# OpenAI text-embedding-3-small vì:
# - sentence-transformers/torch bị treo trên Python 3.14
# - API call ổn định, không cần load model local
# - Hỗ trợ tốt đa ngôn ngữ kể cả tiếng Việt
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

VECTOR_STORE = "chromadb"
COLLECTION_NAME = "drug_law_docs"


# =============================================================================
# IMPLEMENTATION
# =============================================================================

def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': {'source': str, 'type': str}}
    """
    documents = []
    for md_file in STANDARDIZED_DIR.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            print(f"  ⚠ Bỏ qua (rỗng): {md_file.name}")
            continue
        doc_type = "legal" if "legal" in str(md_file) else "news"
        documents.append({
            "content": content,
            "metadata": {
                "source": md_file.name,
                "type": doc_type,
                "path": str(md_file),
            }
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents bằng RecursiveCharacterTextSplitter.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            chunks.append({
                "content": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "total_chunks": len(splits),
                }
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng OpenAI text-embedding-3-small.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    texts = [c["content"] for c in chunks]
    print(f"  Đang embed {len(texts)} chunks qua OpenAI API...")

    # Gửi theo batch 100 để tránh quá tải
    batch_size = 100
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
        print(f"  Embedded batch {i // batch_size + 1}: {len(batch)} chunks")

    for chunk, emb in zip(chunks, all_embeddings):
        chunk["embedding"] = emb

    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào ChromaDB (local).
    """
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Xoá collection cũ nếu có (để chạy lại từ đầu)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  Đã xoá collection cũ: {COLLECTION_NAME}")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # dùng cosine similarity
    )

    # Chia thành batch 100 để tránh quá tải
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        collection.add(
            ids=[f"chunk_{i + j}" for j in range(len(batch))],
            documents=[c["content"] for c in batch],
            embeddings=[c["embedding"] for c in batch],
            metadatas=[c["metadata"] for c in batch],
        )
        print(f"  Indexed batch {i // batch_size + 1}: {len(batch)} chunks")

    print(f"  Tổng số chunks trong collection: {collection.count()}")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE} (lưu tại {CHROMA_DIR})")
    print("=" * 50)

    print("\n[1/4] Load documents...")
    docs = load_documents()
    print(f"  ✓ Đọc được {len(docs)} documents")

    print("\n[2/4] Chunking...")
    chunks = chunk_documents(docs)
    print(f"  ✓ Tạo được {len(chunks)} chunks")

    print("\n[3/4] Embedding...")
    chunks = embed_chunks(chunks)
    print(f"  ✓ Đã embed {len(chunks)} chunks")

    print("\n[4/4] Indexing vào ChromaDB...")
    index_to_vectorstore(chunks)
    print("  ✓ Indexed xong")

    print(f"\n✓ Hoàn thành! Vector store lưu tại: {CHROMA_DIR}")


if __name__ == "__main__":
    run_pipeline()

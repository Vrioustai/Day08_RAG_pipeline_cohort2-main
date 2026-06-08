"""
Task 8 — PageIndex Vectorless RAG.

PageIndex là RAG không dùng vector — thay vào đó xây dựng cây thư mục phân cấp
(hierarchical tree index) từ document, rồi dùng LLM để reasoning tìm đúng phần
cần thiết. Không cần embedding, không cần vector store.

Cách hoạt động:
    1. Submit PDF → PageIndex phân tích cấu trúc → tạo tree index
    2. submit_query(doc_id, query) → trả về retrieval_id
    3. get_retrieval(retrieval_id) → trả về kết quả khi sẵn sàng
    4. Hoặc dùng chat_completions() để chat trực tiếp

Lưu ý: submit_document() chỉ nhận file PDF (không nhận markdown).
Dùng làm fallback khi hybrid search (semantic + lexical) không đủ tốt.

Cài đặt:
    pip install pageindex

Đăng ký: https://pageindex.ai/
"""

import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"

# File lưu doc_id đã upload để không upload lại mỗi lần
DOC_ID_FILE = Path(__file__).parent.parent / "data" / "pageindex_doc_ids.json"

_pi_client = None


def _get_client():
    global _pi_client
    if _pi_client is None:
        from pageindex import PageIndexClient
        _pi_client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    return _pi_client


def upload_documents() -> dict[str, str]:
    """
    Upload toàn bộ PDF files từ data/landing/legal/ lên PageIndex.
    Lưu doc_id vào file để tái sử dụng.

    Returns:
        dict: {filename -> doc_id}
    """
    # Đọc doc_ids cũ nếu có
    if DOC_ID_FILE.exists():
        existing = json.loads(DOC_ID_FILE.read_text(encoding="utf-8"))
        print(f"  Đã có {len(existing)} doc_id, bỏ qua upload lại: {list(existing.keys())}")
        return existing

    pi = _get_client()
    doc_ids = {}

    # PageIndex chỉ nhận PDF — upload file PDF gốc từ data/landing/legal/
    pdf_files = list((LANDING_DIR / "legal").glob("*.pdf"))
    print(f"  Tìm thấy {len(pdf_files)} PDF files để upload...")

    for pdf_file in pdf_files:
        print(f"  Uploading: {pdf_file.name} ...")
        try:
            result = pi.submit_document(str(pdf_file))
            doc_id = result["doc_id"]
            doc_ids[pdf_file.name] = doc_id
            print(f"    ✓ doc_id: {doc_id}")
        except Exception as e:
            print(f"    ✗ Lỗi: {e}")

    if not doc_ids:
        print("  ✗ Không upload được file nào.")
        return doc_ids

    # Chờ processing hoàn thành
    print("\n  Chờ PageIndex xử lý documents (có thể mất vài phút)...")
    for filename, doc_id in doc_ids.items():
        print(f"  Chờ {filename}...", end=" ", flush=True)
        for _ in range(30):
            try:
                status = pi.get_document(doc_id).get("status", "")
                if status == "completed":
                    print("✓ completed")
                    break
                elif status == "failed":
                    print("✗ failed")
                    break
            except Exception:
                pass
            time.sleep(10)

    # Lưu doc_ids ra file
    DOC_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOC_ID_FILE.write_text(json.dumps(doc_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Đã lưu doc_ids → {DOC_ID_FILE.name}")
    return doc_ids


def get_doc_ids() -> list[str]:
    """Lấy danh sách doc_id đã upload."""
    if not DOC_ID_FILE.exists():
        return []
    return list(json.loads(DOC_ID_FILE.read_text(encoding="utf-8")).values())


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex Chat API.
    Dùng làm fallback khi hybrid search không có kết quả tốt.

    Cơ chế:
        - chat_completions() gửi query kèm doc_id(s)
        - PageIndex dùng LLM tree search để tìm phần liên quan trong document
        - Trả về câu trả lời tổng hợp có citation

    Args:
        query: Câu truy vấn
        top_k: Không dùng (PageIndex tự quyết định)

    Returns:
        List of {
            'content': str,
            'score': float,
            'metadata': dict,
            'source': 'pageindex'
        }
    """
    pi = _get_client()
    doc_ids = get_doc_ids()

    if not doc_ids:
        raise RuntimeError("Chưa upload documents. Gọi upload_documents() trước.")

    try:
        response = pi.chat_completions(
            messages=[{"role": "user", "content": query}],
            doc_id=doc_ids if len(doc_ids) > 1 else doc_ids[0],
            enable_citations=True,
        )
        answer = response["choices"][0]["message"]["content"]
        return [{
            "content": answer,
            "score": 1.0,
            "metadata": {
                "source": "pageindex",
                "doc_ids": doc_ids,
                "query": query,
            },
            "source": "pageindex",
        }]
    except Exception as e:
        raise RuntimeError(f"PageIndex query thất bại: {e}") from e


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("=== Task 8: PageIndex Vectorless RAG ===\n")

        print("[1/2] Upload PDF documents...")
        doc_ids = upload_documents()
        print(f"  Tổng: {len(doc_ids)} documents.\n")

        if doc_ids:
            print("[2/2] Test query...")
            test_queries = [
                "hình phạt tội tàng trữ ma tuý theo luật Việt Nam là bao nhiêu năm tù?",
                "các hành vi bị cấm liên quan đến ma tuý là gì?",
            ]
            for q in test_queries:
                print(f"\nQuery: {q}")
                results = pageindex_search(q, top_k=2)
                for r in results:
                    print(f"  [source={r['metadata']['source']}]\n  {r['content'][:300]}...")

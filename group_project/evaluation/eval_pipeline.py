"""
RAGAS Evaluation Pipeline — Group Project Day 8

Đánh giá RAG pipeline theo 4 metrics:
  - Faithfulness      : câu trả lời bám đúng context không?
  - Answer Relevancy  : trả lời đúng câu hỏi không?
  - Context Recall    : retriever lấy đủ evidence không?
  - Context Precision : context lấy về bao nhiêu % hữu ích?

So sánh A/B:
  - Config A: Hybrid (semantic + BM25) + Reranking (RRF)
  - Config B: Dense-only (semantic search, không BM25, không rerank)

Chạy:
  pip install "ragas>=0.2.0,<0.3.0" datasets openai
  python group_project/evaluation/eval_pipeline.py
"""

import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime

# Thêm root vào sys.path để import src.*
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root))
_src = str(_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from dotenv import load_dotenv
load_dotenv(_root / ".env")


# ──────────────────────────────────────────────
# LOAD GOLDEN DATASET
# ──────────────────────────────────────────────
GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


def load_golden_dataset(categories: list[str] | None = None) -> list[dict]:
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if categories:
        data = [d for d in data if d["category"] in categories]
    return data


# ──────────────────────────────────────────────
# PIPELINE CONFIGS
# ──────────────────────────────────────────────

def run_config_a(query: str, top_k: int = 5) -> dict:
    """
    Config A — Full Hybrid Pipeline (Semantic + BM25 + RRF Rerank)
    Đây là pipeline chính từ Task 9 + Task 10.
    """
    from task9_retrieval_pipeline import retrieve
    from task10_generation import reorder_for_llm, format_context, SYSTEM_PROMPT, TEMPERATURE, TOP_P

    chunks = retrieve(query, top_k=top_k, score_threshold=0.2,
                      use_reranking=True, use_pageindex_fallback=False)
    if not chunks:
        return {"answer": "Không tìm thấy thông tin liên quan.", "sources": [], "contexts": []}

    reordered  = reorder_for_llm(chunks)
    context_str = format_context(reordered)
    contexts   = [c["content"] for c in chunks]

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {"answer": "⚠ OPENAI_API_KEY chưa set.", "sources": chunks, "contexts": contexts}

    from openai import OpenAI
    client = OpenAI(api_key=openai_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context_str}\n\n---\n\nQuestion: {query}"},
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    return {
        "answer":   resp.choices[0].message.content,
        "sources":  chunks,
        "contexts": contexts,
    }


def run_config_b(query: str, top_k: int = 5) -> dict:
    """
    Config B — Dense-only (chỉ Semantic Search, không BM25, không rerank)
    Baseline để so sánh với Config A.
    """
    from task5_semantic_search import semantic_search
    from task10_generation import reorder_for_llm, format_context, SYSTEM_PROMPT, TEMPERATURE, TOP_P

    chunks = semantic_search(query, top_k=top_k)
    if not chunks:
        return {"answer": "Không tìm thấy thông tin liên quan.", "sources": [], "contexts": []}

    reordered   = reorder_for_llm(chunks)
    context_str = format_context(reordered)
    contexts    = [c["content"] for c in chunks]

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {"answer": "⚠ OPENAI_API_KEY chưa set.", "sources": chunks, "contexts": contexts}

    from openai import OpenAI
    client = OpenAI(api_key=openai_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Context:\n{context_str}\n\n---\n\nQuestion: {query}"},
        ],
        temperature=TEMPERATURE,
        top_p=TOP_P,
    )
    return {
        "answer":   resp.choices[0].message.content,
        "sources":  chunks,
        "contexts": contexts,
    }


# ──────────────────────────────────────────────
# BUILD RAGAS DATASET
# ──────────────────────────────────────────────

def build_ragas_dataset(golden: list[dict], run_fn, config_name: str) -> dict:
    """Chạy pipeline trên golden dataset và build dict cho RAGAS."""
    eval_data = {
        "question":    [],
        "answer":      [],
        "contexts":    [],
        "ground_truth":[],
    }

    print(f"\n[{config_name}] Chạy pipeline trên {len(golden)} câu hỏi...")
    for i, item in enumerate(golden, 1):
        q = item["question"]
        print(f"  [{i:02d}/{len(golden)}] {q[:60]}...")
        try:
            result = run_fn(q, top_k=5)
            eval_data["question"].append(q)
            eval_data["answer"].append(result["answer"])
            eval_data["contexts"].append(result["contexts"] if result["contexts"] else [""])
            eval_data["ground_truth"].append(item["expected_answer"])
            time.sleep(0.5)  # tránh rate limit
        except Exception as e:
            print(f"    ⚠ Lỗi: {e}")
            eval_data["question"].append(q)
            eval_data["answer"].append(f"ERROR: {e}")
            eval_data["contexts"].append([""])
            eval_data["ground_truth"].append(item["expected_answer"])

    return eval_data


# ──────────────────────────────────────────────
# FIX RAGAS IMPORT (vertexai stub)
# ──────────────────────────────────────────────

def _patch_vertexai():
    """
    Stub langchain_community.chat_models.vertexai — đã bị xoá trong
    langchain-community >= 0.2. RAGAS cũ vẫn import nó → lỗi.
    """
    import types
    path = "langchain_community.chat_models.vertexai"
    if path not in sys.modules:
        stub = types.ModuleType(path)
        stub.ChatVertexAI = None
        sys.modules[path] = stub
        try:
            import langchain_community.chat_models as p
            p.vertexai = stub
        except Exception:
            pass


# ──────────────────────────────────────────────
# RAGAS EVALUATION
# ──────────────────────────────────────────────

def run_ragas_eval(eval_data: dict, config_name: str) -> dict:
    """
    Chạy RAGAS evaluation với 4 metrics.
    Yêu cầu: pip install "ragas>=0.2.0,<0.3.0" datasets
    """
    _patch_vertexai()
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_recall,
            context_precision,
        )
    except Exception as e:
        print(f"❌ Lỗi import ragas: {type(e).__name__}: {e}")
        print("   Thử: pip install 'ragas>=0.2.0,<0.3.0' datasets")
        return {}

    dataset = Dataset.from_dict(eval_data)
    print(f"\n[{config_name}] Đang chạy RAGAS evaluation ({len(eval_data['question'])} samples)...")

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("  ⚠ OPENAI_API_KEY chưa set — RAGAS cần key để chạy LLM-based metrics")
            return {}

        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas.llms import LangchainLLMWrapper
        from ragas.embeddings import LangchainEmbeddingsWrapper

        ragas_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", api_key=openai_key))
        ragas_emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(api_key=openai_key))

        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
            llm=ragas_llm,
            embeddings=ragas_emb,
        )
        df = result.to_pandas()
        scores = {
            "faithfulness":      round(float(df["faithfulness"].mean(skipna=True)),      4),
            "answer_relevancy":  round(float(df["answer_relevancy"].mean(skipna=True)),  4),
            "context_recall":    round(float(df["context_recall"].mean(skipna=True)),    4),
            "context_precision": round(float(df["context_precision"].mean(skipna=True)), 4),
        }
        scores["overall"] = round(sum(scores.values()) / len(scores), 4)
        return {"scores": scores, "df": df}

    except Exception as e:
        import traceback
        print(f"❌ RAGAS evaluate() lỗi: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        return {}


# ──────────────────────────────────────────────
# SAVE RESULTS.MD
# ──────────────────────────────────────────────

def save_results(results_a: dict, results_b: dict, golden: list[dict]):
    """Lưu kết quả ra results.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_path = Path(__file__).parent / "results.md"

    sa = results_a.get("scores", {})
    sb = results_b.get("scores", {})

    def delta(a_val, b_val):
        if not a_val or not b_val:
            return "—"
        d = a_val - b_val
        return f"+{d:.4f} ↑" if d > 0 else f"{d:.4f} ↓" if d < 0 else "="

    lines = [
        "# RAGAS Evaluation Results",
        "",
        f"**Ngày chạy:** {now}  ",
        f"**Số câu hỏi:** {len(golden)}  ",
        "**Framework:** RAGAS  ",
        "",
        "---",
        "",
        "## Kết quả A/B Comparison",
        "",
        "| Metric | Config A (Hybrid+Rerank) | Config B (Dense-only) | Δ |",
        "|--------|:-----------------------:|:--------------------:|:---:|",
        f"| **Faithfulness** | `{sa.get('faithfulness','N/A')}` | `{sb.get('faithfulness','N/A')}` | {delta(sa.get('faithfulness'), sb.get('faithfulness'))} |",
        f"| **Answer Relevancy** | `{sa.get('answer_relevancy','N/A')}` | `{sb.get('answer_relevancy','N/A')}` | {delta(sa.get('answer_relevancy'), sb.get('answer_relevancy'))} |",
        f"| **Context Recall** | `{sa.get('context_recall','N/A')}` | `{sb.get('context_recall','N/A')}` | {delta(sa.get('context_recall'), sb.get('context_recall'))} |",
        f"| **Context Precision** | `{sa.get('context_precision','N/A')}` | `{sb.get('context_precision','N/A')}` | {delta(sa.get('context_precision'), sb.get('context_precision'))} |",
        f"| **Overall** | `{sa.get('overall','N/A')}` | `{sb.get('overall','N/A')}` | {delta(sa.get('overall'), sb.get('overall'))} |",
        "",
        "---",
        "",
        "## Định nghĩa Metrics",
        "",
        "- **Faithfulness**: Câu trả lời có bám đúng context không? (1.0 = hoàn toàn trung thực với nguồn)",
        "- **Answer Relevancy**: Câu trả lời có đúng câu hỏi không? (1.0 = rất liên quan)",
        "- **Context Recall**: Retriever có lấy đủ evidence từ ground truth không? (1.0 = đủ)",
        "- **Context Precision**: Trong context lấy về, % nào thực sự hữu ích? (1.0 = tất cả đều hữu ích)",
        "",
        "---",
        "",
        "## Phân tích",
        "",
        "### Config A — Hybrid + RRF Reranking",
        "- Kết hợp Semantic Search (ChromaDB, cosine sim) + BM25 (lexical matching)",
        "- RRF Merge gộp 2 ranking lists",
        "- Jina Cross-encoder Rerank để lọc kết quả cuối",
        "- Fallback PageIndex khi semantic score < 0.3",
        "",
        "### Config B — Dense-only (Baseline)",
        "- Chỉ dùng Semantic Search (ChromaDB)",
        "- Không BM25, không rerank",
        "- Phụ thuộc hoàn toàn vào embedding quality",
        "",
        "### Nhận xét",
        "- Context Recall thấp → cần mở rộng corpus (thêm văn bản pháp luật, nhiều bài báo hơn)",
        "- Faithfulness phụ thuộc vào chất lượng LLM và độ rõ ràng của context",
        "- Config A thường tốt hơn Config B ở Context Recall vì BM25 bắt được keyword chính xác",
        "",
        "---",
        "",
        "## Đề xuất cải tiến",
        "",
        "1. **Tăng corpus**: Thêm toàn bộ Bộ luật Hình sự phần ma tuý, nhiều bài báo hơn",
        "2. **Better chunking**: Thử chunk theo điều khoản luật thay vì fixed-size",
        "3. **Cross-encoder reranking**: Dùng Jina Reranker để cải thiện Context Precision",
        "4. **Query expansion**: Tự động mở rộng query với từ đồng nghĩa tiếng Việt",
        "5. **Knowledge graph** (giai đoạn 2): Liên kết điều luật ↔ nghệ sĩ ↔ vụ án",
        "",
        "---",
        "*Generated by RAGAS Evaluation Pipeline — Day 8 Group Project*",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✅ Báo cáo lưu tại: {report_path}")

    # Lưu raw JSON
    raw_path = Path(__file__).parent / "results_raw.json"
    raw = {}
    if results_a.get("df") is not None:
        raw["config_a"] = results_a["df"].to_dict(orient="records")
    if results_b.get("df") is not None:
        raw["config_b"] = results_b["df"].to_dict(orient="records")
    if raw:
        raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Raw data lưu tại: {raw_path}")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("RAGAS Evaluation Pipeline — DrugLaw RAG")
    print("=" * 60)

    golden = load_golden_dataset()
    print(f"Loaded {len(golden)} test cases")
    print(f"  legal: {sum(1 for d in golden if d['category']=='legal')}")
    print(f"  news:  {sum(1 for d in golden if d['category']=='news')}")
    print(f"  mixed: {sum(1 for d in golden if d['category']=='mixed')}")

    # Build datasets cho cả 2 config
    data_a = build_ragas_dataset(golden, run_config_a, "Config A: Hybrid+Rerank")
    data_b = build_ragas_dataset(golden, run_config_b, "Config B: Dense-only")

    # RAGAS evaluation
    results_a = run_ragas_eval(data_a, "Config A")
    results_b = run_ragas_eval(data_b, "Config B")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if results_a.get("scores"):
        print("\nConfig A (Hybrid + RRF Rerank):")
        for k, v in results_a["scores"].items():
            print(f"  {k:<25} {v:.4f}")
    if results_b.get("scores"):
        print("\nConfig B (Dense-only):")
        for k, v in results_b["scores"].items():
            print(f"  {k:<25} {v:.4f}")

    save_results(results_a, results_b, golden)


if __name__ == "__main__":
    main()

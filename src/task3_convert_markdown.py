"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Cài đặt:
    pip install markitdown

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

import json
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()

    files = [f for f in legal_dir.iterdir() if f.suffix.lower() in (".pdf", ".docx", ".doc")]
    if not files:
        print("  (Không có file PDF/DOCX nào)")
        return

    for filepath in files:
        print(f"Converting: {filepath.name}")
        try:
            result = md.convert(str(filepath))
            output_path = output_dir / f"{filepath.stem}.md"
            output_path.write_text(result.text_content, encoding="utf-8")
            print(f"  ✓ Saved: {output_path.name}  ({len(result.text_content)} chars)")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    files = [f for f in news_dir.iterdir() if f.suffix.lower() == ".json"]
    if not files:
        print("  (Không có file JSON nào)")
        return

    for filepath in sorted(files):
        print(f"Converting: {filepath.name}")
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            output_path = output_dir / f"{filepath.stem}.md"

            # Thêm metadata header
            header = f"# {data.get('title', 'Unknown')}\n\n"
            header += f"**Source:** {data.get('url', 'N/A')}\n\n"
            header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n"
            header += "---\n\n"

            content = header + data.get("content_markdown", "")
            output_path.write_text(content, encoding="utf-8")
            print(f"  ✓ Saved: {output_path.name}  ({len(content)} chars)")
        except Exception as e:
            print(f"  ✗ Error: {e}")


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    print("\n--- Legal Documents ---")
    convert_legal_docs()

    print("\n--- News Articles ---")
    convert_news_articles()

    print("\n✓ Done! Output tại:", OUTPUT_DIR)


if __name__ == "__main__":
    convert_all()

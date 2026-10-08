"""从 PDF 快照提取文本 -> artifacts/extracted/{slug}.txt（供引用校验与 LLM 抽取使用）。"""
import re
from pathlib import Path

from pypdf import PdfReader

from src.fetch.common import ROOT

OUT = ROOT / "artifacts" / "extracted"


def slug_of(pdf_path: Path) -> str:
    m = re.match(r"\d{8}T\d{6}Z_(.+)\.pdf$", pdf_path.name)
    return m.group(1) if m else pdf_path.stem


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for pdf in sorted((ROOT / "data" / "snapshots" / "company_pr").glob("*.pdf")):
        slug = slug_of(pdf)
        out = OUT / f"{slug}.txt"
        if out.exists():
            continue
        try:
            reader = PdfReader(str(pdf))
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
            out.write_text(text, encoding="utf-8")
            print(f"[pdf] {slug}: {len(reader.pages)} pages, {len(text)} chars")
        except Exception as e:
            print(f"[pdf] {slug}: FAILED {type(e).__name__} {e}")


if __name__ == "__main__":
    main()

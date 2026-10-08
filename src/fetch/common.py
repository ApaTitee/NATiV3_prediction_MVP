"""Snapshot writer + manifest. 一切抓取先写盘，下游只读快照。"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
SNAP_DIR = ROOT / "data" / "snapshots"
MANIFEST = SNAP_DIR / "manifest.csv"
MANIFEST_COLS = ["source", "url", "retrieved_at_utc", "sha256", "http_status", "bytes", "path"]

HEADERS = {"User-Agent": "nativ3-mvp/1.0 (academic reproducibility project; contact: none)"}


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _append_manifest(row: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    exists = MANIFEST.exists()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def save_snapshot(source: str, url: str, slug: str, content: bytes,
                  http_status: int, retrieved_at: str, ext: str = ".json") -> Path:
    ts = retrieved_at.replace(":", "").replace("-", "")
    out_dir = SNAP_DIR / source
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ts}_{slug}{ext}"
    path.write_bytes(content)
    _append_manifest({
        "source": source, "url": url, "retrieved_at_utc": retrieved_at,
        "sha256": sha256_bytes(content), "http_status": http_status,
        "bytes": len(content), "path": str(path.relative_to(ROOT)),
    })
    return path


def fetch_and_snapshot(source: str, url: str, slug: str, ext: str = ".json",
                       timeout: int = 60) -> tuple[Path, bytes]:
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    retrieved_at = utcnow()
    path = save_snapshot(source, url, slug, r.content, r.status_code, retrieved_at, ext)
    return path, r.content


def load_json(path: str | Path):
    return json.loads(Path(path).read_bytes())

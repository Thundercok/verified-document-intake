import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / "dataset"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"dataset_{name}", ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build = _load("build")
download = _load("download")


def test_build_helpers():
    assert build.doc_id(1, 7) == "vbcp1-0007"
    assert build.iso("05/03/2026") == build.iso([5, 3, 2026]) == "2026-03-05"
    assert build.iso(None) is None
    assert build.normalize_number("47 /2026/QÐ-UBND") == "47/2026/QĐ-UBND"
    assert build.normalize_number("12/QĐ-ТТg") == "12/QĐ-TTg"  # Cyrillic Т
    assert build.crop_key("data/private/vbcp/pages/012/head_drop.png") == ("vbcp1-0012", "head_drop")
    assert build.crop_key("/x/data/private/vbcp8/pages/430/auth7_small.png") == ("vbcp8-0430", "auth7_small")
    assert build.crop_key("data/private/vbcp8/pdf/430.pdf") is None


def test_label_prefers_adjudication():
    listing = {"number": "33/2025/TT-BNNMT", "date": "02/07/2025"}
    assert build.label(listing, None) == {"number": "33/2025/TT-BNNMT", "date": "2025-07-02", "source": "listing"}
    adj = {"number": "33/2025/TT-BTNMT", "date": "02/07/2025"}
    assert build.label(listing, adj)["source"] == "adjudicated"


def test_pii_screen_flags_ids_and_allows_known_contexts():
    synth = "079203000001"  # synthetic
    hits = build.pii_hits([{"doc_id": "x", "crop": "head", "text": f"Số CCCD {synth}"}])
    assert hits and "XXXXXX000001" in hits[0][2] and synth not in hits[0][2]
    assert build.pii_hits([{"doc_id": "x", "crop": "head", "text": "Căn cứ Luật Căn cước năm 2023"}]) == []
    assert build.pii_hits([{"doc_id": "x", "crop": "head", "text": "Số: 123/CĐ-TTg ngày 27 tháng 7"}]) == []


def test_gzip_output_is_reproducible():
    data = build.jsonl([{"b": 1, "a": "đ"}])
    assert data == '{"a": "đ", "b": 1}\n'.encode()
    assert build.gz(data) == build.gz(data)


@pytest.fixture
def docs():
    good, bad = b"%PDF-good", b"%PDF-changed"
    return [
        {"doc_id": "a", "url": "u/a", "pdf_sha256": download.digest(good), "pdf_bytes": len(good)},
        {"doc_id": "b", "url": "u/b", "pdf_sha256": download.digest(good), "pdf_bytes": len(good)},
        {"doc_id": "c", "url": "u/c", "pdf_sha256": download.digest(good), "pdf_bytes": len(good)},
    ], {"u/a": good, "u/b": bad}


def test_download_checks_hash_reports_failures_and_resumes(tmp_path, docs):
    index, files = docs
    calls = []

    def get(url):
        calls.append(url)
        if url not in files:
            raise OSError("404")
        return files[url]

    failures = dict(download.download(index, tmp_path, delay=0, get=get))
    assert (tmp_path / "a.pdf").read_bytes() == b"%PDF-good"
    assert not (tmp_path / "b.pdf").exists() and "sha256 differs" in failures["b"]
    assert "fetch failed" in failures["c"]
    calls.clear()
    download.download(index, tmp_path, delay=0, get=get)
    assert calls == ["u/b", "u/c"]  # a is present with the right hash: not fetched again


def test_released_index_is_consistent():
    path = ROOT / "vbcp-numdate" / "documents.jsonl"
    if not path.exists():
        pytest.skip("release not built")
    docs = [json.loads(line) for line in path.open(encoding="utf-8")]
    assert len({d["doc_id"] for d in docs}) == len(docs) == len({d["url"] for d in docs})
    assert all(len(d["pdf_sha256"]) == 64 and d["url"].startswith("https://datafiles.chinhphu.vn/") for d in docs)
    assert {d["label"]["source"] for d in docs} <= {"listing", "adjudicated"}
    meta = json.loads((ROOT / "vbcp-numdate" / "croissant.json").read_text(encoding="utf-8"))
    files = {f["name"]: f["sha256"] for f in meta["distribution"]}
    for name, sha in files.items():
        assert download.digest((ROOT / "vbcp-numdate" / name).read_bytes()) == sha

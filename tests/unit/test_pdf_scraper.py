from pathlib import Path
import json

import pytest

from scraper.config import load_config
from scraper.merger import merge_pdfs

try:  # pragma: no cover - optional dependency
    from PyPDF2 import PdfReader, PdfWriter
except Exception:  # pragma: no cover - package may not be installed
    PdfReader = PdfWriter = None


def _create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as fh:
        writer.write(fh)


def test_load_config(tmp_path):
    cfg = [{"url": "https://a", "city": "X", "selectors": ["a[href$='.pdf']"]}]
    file = tmp_path / "sites.json"
    file.write_text(json.dumps(cfg))
    sites = load_config(file)
    assert sites[0].city == "X"
    assert sites[0].selectors == ["a[href$='.pdf']"]


@pytest.mark.skipif(PdfReader is None, reason="PyPDF2 not installed")
def test_merge_pdfs(tmp_path):
    p1 = tmp_path / "a.pdf"
    p2 = tmp_path / "b.pdf"
    _create_pdf(p1)
    _create_pdf(p2)
    output = tmp_path / "out.pdf"
    merge_pdfs([p1, p2], output)
    reader = PdfReader(str(output))
    assert len(reader.pages) == 2

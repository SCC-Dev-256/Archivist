from __future__ import annotations

import os
from pathlib import Path

from scraper.pipelines import PdfFilesPipeline


def test_file_path_sanitization(tmp_path, monkeypatch):
    pipeline = PdfFilesPipeline(store_uri=str(tmp_path))
    class DummyItem(dict):
        pass
    item = DummyItem(city='My City')
    request = type('R', (), {'url': 'https://example.com/unsafe/..//name..pdf'})
    path = pipeline.file_path(request, item=item)
    # Should strip dangerous chars and keep .pdf
    assert path.startswith('pdfs/my_city/')
    assert path.endswith('.pdf')
    assert '..' not in path



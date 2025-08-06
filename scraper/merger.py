from __future__ import annotations

from pathlib import Path
from typing import Iterable


def merge_pdfs(pdfs: Iterable[Path], output: Path) -> Path:
    """Merge *pdfs* into *output* and return the resulting path."""

    from PyPDF2 import PdfMerger

    merger = PdfMerger()
    for pdf in pdfs:
        merger.append(str(pdf))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as fh:
        merger.write(fh)
    merger.close()
    return output

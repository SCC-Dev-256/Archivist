from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import logging

logger = logging.getLogger(__name__)


def merge_pdfs(pdfs: Iterable[Path], output: Path, max_total_bytes: int = 200 * 1024 * 1024) -> Optional[Path]:
    """Safely merge *pdfs* into *output* using pypdf's PdfWriter (pypdf>=5).

    - Skips missing or zero-byte files
    - Enforces a total size ceiling to avoid DoS
    - Catches parser errors and continues

    Returns the output path on success, or None if nothing was merged.
    """

    from pypdf import PdfWriter, PdfReader
    try:
        from pypdf.errors import PdfReadError
    except Exception:  # pragma: no cover
        PdfReadError = Exception

    output.parent.mkdir(parents=True, exist_ok=True)

    writer = PdfWriter()
    total_bytes = 0
    files_added = 0

    for pdf in pdfs:
        try:
            if not pdf.exists():
                logger.warning(f"Skipping missing file: {pdf}")
                continue
            size = pdf.stat().st_size
            if size == 0:
                logger.warning(f"Skipping empty file: {pdf}")
                continue
            if total_bytes + size > max_total_bytes:
                logger.error(
                    f"Aborting merge: size limit exceeded at {pdf} (total would be {total_bytes + size} bytes)"
                )
                break

            # Prefer fast append API if available; fallback to manual page copy
            try:
                append = getattr(writer, "append")
            except AttributeError:
                append = None

            if append is not None:
                append(str(pdf))
            else:
                reader = PdfReader(str(pdf))
                for page in reader.pages:
                    writer.add_page(page)

            total_bytes += size
            files_added += 1
        except (PdfReadError, Exception) as exc:
            logger.error(f"Failed to append {pdf}: {exc}")
            continue

    if files_added == 0:
        logger.error("No valid PDFs to merge; nothing written")
        return None

    with output.open("wb") as fh:
        writer.write(fh)
    logger.info(f"Merged {files_added} PDFs into {output} ({total_bytes} bytes)")
    return output

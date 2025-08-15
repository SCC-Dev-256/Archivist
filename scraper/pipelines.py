from __future__ import annotations

# PURPOSE: Centralized Scrapy pipelines for PDF downloads and validation
# DEPENDENCIES: scrapy, FilesPipeline
# MODIFICATION NOTES: v2.0 - Add SHA256 checksums, duplicate skipping, and manifest writing

import os
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List

import scrapy
from scrapy.pipelines.files import FilesPipeline
from scrapy.http import Request


class PdfFilesPipeline(FilesPipeline):
    def open_spider(self, spider):
        self._seen_sha256: set[str] = set()
        self._manifest: List[Dict[str, Any]] = []
        # Optional Prometheus counters
        try:
            from prometheus_client import Counter
            self._metric_downloaded = Counter('pdf_downloaded_total', 'Downloaded PDFs')
            self._metric_bytes = Counter('pdf_downloaded_bytes_total', 'Downloaded PDF bytes')
            self._metric_duplicates = Counter('pdf_duplicates_total', 'Duplicate PDFs skipped')
            self._metric_rejected = Counter('pdf_rejected_total', 'Rejected items (type/other)')
        except Exception:
            self._metric_downloaded = self._metric_bytes = self._metric_duplicates = self._metric_rejected = None
        super().open_spider(spider)

    def file_path(self, request: Request, response=None, info=None, *, item=None) -> str:
        city = (item or {}).get('city', 'unknown').lower().replace(' ', '_')
        parsed = urlparse(request.url)
        filename = os.path.basename(parsed.path) or 'download.pdf'
        # Sanitize filename, keep only safe chars and collapse repeated dots
        safe_name = ''.join(ch for ch in filename if ch.isalnum() or ch in ('-', '_', '.'))
        while '..' in safe_name:
            safe_name = safe_name.replace('..', '.')
        safe_name = safe_name.lstrip('.')
        if not safe_name:
            safe_name = 'download.pdf'
        if not safe_name.lower().endswith('.pdf'):
            safe_name = f"{safe_name}.pdf"
        return f"pdfs/{city}/{safe_name}"

    def get_media_requests(self, item, info):
        for url in item.get('file_urls', []):
            yield Request(url, headers={'Accept': 'application/pdf'})

    def media_downloaded(self, response, request, info, *, item=None):
        # Content-Type must be PDF-ish
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        if 'application/pdf' not in content_type and not request.url.lower().endswith('.pdf'):
            if self._metric_rejected:
                self._metric_rejected.inc()
            raise scrapy.exceptions.DropItem(f"Non-PDF content-type for {request.url}: {content_type}")

        # Compute SHA256 to detect duplicates pre-write
        body = response.body or b''
        sha256 = hashlib.sha256(body).hexdigest()
        request.meta['sha256'] = sha256
        if sha256 in getattr(self, '_seen_sha256', set()):
            request.meta['duplicate'] = True
            if self._metric_duplicates:
                self._metric_duplicates.inc()
        else:
            self._seen_sha256.add(sha256)
            request.meta['duplicate'] = False

        if self._metric_downloaded:
            self._metric_downloaded.inc()
        if self._metric_bytes:
            self._metric_bytes.inc(len(body))
        return super().media_downloaded(response, request, info, item=item)

    def item_completed(self, results, item, info):
        # results: list of tuples (ok, info_dict)
        for ok, result in results:
            if not ok:
                continue
            path = result.get('path')
            url = result.get('url')
            checksum_md5 = result.get('checksum')  # default FilesPipeline md5
            sha256 = None
            duplicate = False
            # Get values back from meta if present
            for req in info.requests:
                if req.url == url:
                    sha256 = req.meta.get('sha256')
                    duplicate = req.meta.get('duplicate', False)
                    break

            # If duplicate, remove the stored file and skip manifest entry
            if duplicate and path:
                store_base = info.spider.settings.get('FILES_STORE', 'downloads')
                try:
                    full_path = Path(store_base) / path
                    if full_path.exists():
                        full_path.unlink()
                except Exception:
                    pass
                continue

            # Build manifest entry
            if path:
                store_base = info.spider.settings.get('FILES_STORE', 'downloads')
                full_path = Path(store_base) / path
                size = full_path.stat().st_size if full_path.exists() else None
                self._manifest.append({
                    'path': str(full_path),
                    'relative_path': path,
                    'url': url,
                    'city': item.get('city'),
                    'md5': checksum_md5,
                    'sha256': sha256,
                    'size_bytes': size,
                })

        return item

    def close_spider(self, spider):
        # Write manifest to FILES_STORE/manifest.json
        store_base = spider.settings.get('FILES_STORE', 'downloads')
        out_dir = Path(store_base)
        out_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = out_dir / 'manifest.json'
        with manifest_path.open('w', encoding='utf-8') as fh:
            json.dump({'files': self._manifest}, fh, indent=2)
        super().close_spider(spider)



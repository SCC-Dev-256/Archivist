from __future__ import annotations

# PURPOSE: Simple CLI to validate config, crawl, and merge with manifest output and optional webhook
# DEPENDENCIES: argparse, json, pathlib, requests (optional webhook)
# MODIFICATION NOTES: v1.0 - Minimal surface for operational usage

import argparse
import json
from pathlib import Path
from typing import List

from .config import load_config
from .main import CityScraper
from .merger import merge_pdfs


def main():
    parser = argparse.ArgumentParser(prog='scraper-cli')
    parser.add_argument('--config', default='scraper/sites.json')
    parser.add_argument('--merge-dir', default='downloads/pdfs')
    parser.add_argument('--output', default='downloads/combined.pdf')
    parser.add_argument('--webhook-url', default=None)
    parser.add_argument('--max-merge-bytes', type=int, default=200 * 1024 * 1024)
    args = parser.parse_args()

    # Validate config
    sites = load_config(args.config)
    print(f"Loaded {len(sites)} sites from {args.config}")

    # Crawl
    scraper = CityScraper(config_path=args.config)
    results = scraper.run()
    print(f"Discovered {len(results)} PDF URLs")

    # Merge all PDFs in merge-dir
    merge_dir = Path(args.merge_dir)
    pdfs: List[Path] = [p for p in merge_dir.rglob('*.pdf') if p.is_file()]
    print(f"Found {len(pdfs)} local PDFs to merge from {merge_dir}")
    out = merge_pdfs(pdfs, Path(args.output), max_total_bytes=args.max_merge_bytes)
    if out is None:
        print("No PDFs merged; exiting")
        return 1

    manifest_path = Path('downloads') / 'manifest.json'
    print(f"Manifest: {manifest_path if manifest_path.exists() else 'not created'}")
    print(f"Merged: {out}")

    # Optional webhook
    if args.webhook_url:
        try:
            import requests
            payload = {
                'artifact_path': str(out),
                'manifest_path': str(manifest_path) if manifest_path.exists() else None,
            }
            resp = requests.post(args.webhook_url, json=payload, timeout=10)
            print(f"Webhook status: {resp.status_code}")
        except Exception as exc:
            print(f"Webhook failed: {exc}")

    return 0


if __name__ == '__main__':
    raise SystemExit(main())



from __future__ import annotations

# PURPOSE: Downloader middleware to enforce offsite and Content-Length caps early
# DEPENDENCIES: scrapy, optional prometheus_client, optional redis
# MODIFICATION NOTES: v2.0 - Add Prometheus counters and optional Redis HEAD cache

import os
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.exceptions import IgnoreRequest

try:  # optional Prometheus
    from prometheus_client import Counter
    REQUESTS_HEAD = Counter('pdf_head_requests_total', 'HEAD preflight requests')
    BLOCKED_OFFSITE = Counter('pdf_blocked_offsite_total', 'Requests blocked for offsite domain')
    BLOCKED_TYPE = Counter('pdf_blocked_type_total', 'Requests blocked for non-PDF content-type')
    BLOCKED_SIZE = Counter('pdf_blocked_size_total', 'Requests blocked for excessive size')
    PASSED = Counter('pdf_passed_total', 'Requests passed to body download')
except Exception:  # pragma: no cover - metrics optional
    REQUESTS_HEAD = BLOCKED_OFFSITE = BLOCKED_TYPE = BLOCKED_SIZE = PASSED = None

try:  # optional Redis
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional
    redis = None


class EarlyGuardMiddleware:
    def __init__(self, max_content_length: int = 50 * 1024 * 1024, head_cache_ttl: int = 3600, redis_url: Optional[str] = None):
        self.max_content_length = max_content_length
        self.head_cache_ttl = head_cache_ttl
        self.redis = None
        if redis_url and redis is not None:
            try:
                self.redis = redis.from_url(redis_url)
            except Exception:
                self.redis = None
        self._memcache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def from_crawler(cls, crawler):
        max_len = crawler.settings.getint('MAX_CONTENT_LENGTH', 50 * 1024 * 1024)
        ttl = crawler.settings.getint('HEAD_CACHE_TTL', 3600)
        redis_url = os.getenv('REDIS_URL')
        mw = cls(max_len, ttl, redis_url)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        pass

    def _get_cache(self, url: str) -> Optional[Dict[str, Any]]:
        key = f"head:{url}"
        if self.redis is not None:
            try:
                data = self.redis.get(key)
                if data:
                    import json
                    return json.loads(data)
            except Exception:
                return None
        return self._memcache.get(key)

    def _set_cache(self, url: str, value: Dict[str, Any]) -> None:
        key = f"head:{url}"
        if self.redis is not None:
            try:
                import json
                self.redis.setex(key, self.head_cache_ttl, json.dumps(value))
                return
            except Exception:
                pass
        self._memcache[key] = value

    def process_request(self, request: Request, spider):
        # Offsite early check against allowed_domains
        if spider.allowed_domains:
            host = urlparse(request.url).hostname
            if host and host not in spider.allowed_domains:
                if BLOCKED_OFFSITE:
                    BLOCKED_OFFSITE.inc()
                raise IgnoreRequest(f"Offsite blocked: {request.url}")

        if request.method != 'GET':
            return None

        cached = self._get_cache(request.url)
        if cached is not None:
            if not cached.get('ok'):
                if BLOCKED_TYPE:
                    BLOCKED_TYPE.inc()
                raise IgnoreRequest(f"Cached not-PDF or too-large: {request.url}")
            # Allowed
            if PASSED:
                PASSED.inc()
            return request.replace(method='GET', dont_filter=True)

        # For GETs, send a HEAD preflight to check content-type and length
        if REQUESTS_HEAD:
            REQUESTS_HEAD.inc()
        head_req = request.replace(method='HEAD', dont_filter=True)
        return head_req

    def process_response(self, request: Request, response: Response, spider):
        # Evaluate HEAD responses
        if request.method == 'HEAD':
            content_type = response.headers.get('Content-Type', b'').decode('utf-8', 'ignore')
            length_header = response.headers.get('Content-Length')
            if 'application/pdf' not in content_type and not request.url.lower().endswith('.pdf'):
                self._set_cache(request.url, {'ok': False, 'reason': 'type'})
                if BLOCKED_TYPE:
                    BLOCKED_TYPE.inc()
                raise IgnoreRequest(f"Content-Type blocked: {content_type} {request.url}")
            if length_header is not None:
                try:
                    size = int(length_header)
                    if size > self.max_content_length:
                        self._set_cache(request.url, {'ok': False, 'reason': 'size', 'size': size})
                        if BLOCKED_SIZE:
                            BLOCKED_SIZE.inc()
                        raise IgnoreRequest(f"Too large ({size} bytes): {request.url}")
                except ValueError:
                    pass
            # Allowed: cache allow and convert to original GET
            self._set_cache(request.url, {'ok': True, 'content_type': content_type})
            if PASSED:
                PASSED.inc()
            get_req = request.replace(method='GET', dont_filter=True)
            return get_req

        # For GET responses, enforce size by checking length header if present
        length_header = response.headers.get('Content-Length')
        if length_header is not None:
            try:
                size = int(length_header)
                if size > self.max_content_length:
                    if BLOCKED_SIZE:
                        BLOCKED_SIZE.inc()
                    raise IgnoreRequest(f"Too large ({size} bytes): {response.url}")
            except ValueError:
                pass
        return response



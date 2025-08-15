from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import TCPServer
from functools import partial

import pytest
from scrapy.http import Request

from scraper.middlewares import EarlyGuardMiddleware


class _Handler(BaseHTTPRequestHandler):
    mode = 'pdf'  # 'pdf', 'nonpdf', 'large'

    def do_HEAD(self):
        if self.mode == 'pdf':
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', '1024')
            self.end_headers()
        elif self.mode == 'nonpdf':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', '1024')
            self.end_headers()
        elif self.mode == 'large':
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(100 * 1024 * 1024))
            self.end_headers()

    def do_GET(self):  # not actually used by mw test
        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Length', '10')
        self.end_headers()
        self.wfile.write(b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n')


class DummySpider:
    allowed_domains = []
    settings = {'MAX_CONTENT_LENGTH': 1024 * 1024}


def _run_server(mode):
    server = HTTPServer(('127.0.0.1', 0), _Handler)
    _Handler.mode = mode
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_early_guard_allows_pdf_head():
    server = _run_server('pdf')
    try:
        url = f'http://127.0.0.1:{server.server_port}/doc.pdf'
        mw = EarlyGuardMiddleware(max_content_length=1024 * 1024)
        req = Request(url)
        # First call converts to HEAD
        head = mw.process_request(req, DummySpider())
        assert head.method == 'HEAD'
        # Simulate HEAD response
        from scrapy.http import Response
        resp = Response(url=url, headers={b'Content-Type': b'application/pdf', b'Content-Length': b'1024'})
        out = mw.process_response(head, resp, DummySpider())
        assert isinstance(out, Request) and out.method == 'GET'
    finally:
        server.shutdown()


def test_early_guard_blocks_nonpdf():
    server = _run_server('nonpdf')
    try:
        url = f'http://127.0.0.1:{server.server_port}/doc'
        mw = EarlyGuardMiddleware(max_content_length=1024 * 1024)
        req = Request(url)
        head = mw.process_request(req, DummySpider())
        from scrapy.http import Response
        resp = Response(url=url, headers={b'Content-Type': b'text/html', b'Content-Length': b'1024'})
        import pytest
        with pytest.raises(Exception):
            mw.process_response(head, resp, DummySpider())
    finally:
        server.shutdown()


def test_early_guard_blocks_large():
    server = _run_server('large')
    try:
        url = f'http://127.0.0.1:{server.server_port}/doc.pdf'
        mw = EarlyGuardMiddleware(max_content_length=1024 * 1024)
        req = Request(url)
        head = mw.process_request(req, DummySpider())
        from scrapy.http import Response
        too_big = 100 * 1024 * 1024
        resp = Response(url=url, headers={b'Content-Type': b'application/pdf', b'Content-Length': str(too_big).encode()})
        with pytest.raises(Exception):
            mw.process_response(head, resp, DummySpider())
    finally:
        server.shutdown()


def test_offsite_blocking():
    mw = EarlyGuardMiddleware(max_content_length=1024 * 1024)
    spider = type('S', (), {'allowed_domains': ['allowed.example']})()
    req = Request('http://disallowed.example/file.pdf')
    with pytest.raises(Exception):
        mw.process_request(req, spider)


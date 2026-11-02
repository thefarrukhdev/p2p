#!/usr/bin/env python3
"""Lightweight mock Telegram Bot API server for local isolated staging.

Implements getMe, deleteWebhook, getUpdates, sendMessage, and inspection endpoints.
Does not make any external network requests.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MOCK-TG] %(message)s")
logger = logging.getLogger("mock_telegram")

SENT_MESSAGES: list[dict] = []


class MockTelegramHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_method(self, method: str, token: str, payload: dict):
        logger.info("Method: %s (token prefix: %s...)", method, token[:6] if len(token) >= 6 else token)

        if method == "getMe":
            self._send_json(200, {
                "ok": True,
                "result": {
                    "id": 999999999,
                    "is_bot": True,
                    "first_name": "P2P Staging Bot",
                    "username": "p2p_staging_bot",
                    "can_join_groups": True,
                    "can_read_all_group_messages": False,
                    "supports_inline_queries": False,
                }
            })
        elif method == "deleteWebhook":
            self._send_json(200, {
                "ok": True,
                "result": True,
                "description": "Webhook was deleted",
            })
        elif method == "getUpdates":
            import time
            timeout = 1
            if payload and "timeout" in payload:
                try:
                    timeout = min(int(payload["timeout"]), 2)
                except Exception:
                    timeout = 1
            time.sleep(max(timeout, 1))
            self._send_json(200, {
                "ok": True,
                "result": [],
            })
        elif method == "sendMessage":
            chat_id = payload.get("chat_id", 0)
            text = payload.get("text", "")
            record = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": payload.get("parse_mode", "HTML"),
            }
            SENT_MESSAGES.append(record)
            logger.info("Captured sendMessage to chat_id=%s, length=%d", chat_id, len(text))
            self._send_json(200, {
                "ok": True,
                "result": {
                    "message_id": len(SENT_MESSAGES),
                    "date": 1700000000,
                    "chat": {"id": chat_id, "type": "private"},
                    "text": text,
                }
            })
        elif method in ("getMyCommands", "getMyDefaultAdministratorRights"):
            self._send_json(200, {"ok": True, "result": []})
        elif method in ("setMyCommands", "setChatMenuButton", "setMyDescription"):
            self._send_json(200, {"ok": True, "result": True})
        else:
            self._send_json(200, {"ok": True, "result": {}})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "mock-telegram"})
            return
        if parsed.path == "/_mock/sent_messages":
            self._send_json(200, {"count": len(SENT_MESSAGES), "messages": SENT_MESSAGES})
            return

        # Match /bot<token>/<method> or /bot/<token>/<method>
        match = re.match(r"^/bot/?([^/]+)/([a-zA-Z0-9_]+)$", parsed.path)
        if match:
            token, method = match.group(1), match.group(2)
            query_params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            self._handle_method(method, token, query_params)
            return

        self._send_json(404, {"ok": False, "error_code": 404, "description": "Not Found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/_mock/sent_messages":
            global SENT_MESSAGES
            SENT_MESSAGES.clear()
            self._send_json(200, {"ok": True, "cleared": True})
            return
        self._send_json(404, {"ok": False, "error_code": 404})

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else b""
        payload = {}
        if body:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                try:
                    payload = {k: v[0] for k, v in parse_qs(body.decode("utf-8")).items()}
                except Exception:
                    payload = {}

        parsed = urlparse(self.path)
        path = parsed.path

        # Match /bot<token>/<method> or /bot/<token>/<method>
        match = re.match(r"^/bot/?([^/]+)/([a-zA-Z0-9_]+)$", path)
        if not match:
            self._send_json(404, {"ok": False, "error_code": 404, "description": f"Unknown endpoint {path}"})
            return

        token, method = match.group(1), match.group(2)
        self._handle_method(method, token, payload)

    def log_message(self, format, *args):
        # Suppress routine log output to keep container logs clean
        pass


def run(port: int = 8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), MockTelegramHandler)
    logger.info("Mock Telegram server listening on 0.0.0.0:%d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping mock server...")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port)

#!/usr/bin/env python3
"""Lightweight mock School 21 & Keycloak API server for local staging.

Provides deterministic responses for Keycloak password grant and
School 21 participant profile / workstation / skills endpoints.
Does not make any external network requests.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [MOCK-S21] %(message)s")
logger = logging.getLogger("mock_school21")


class MockSchool21Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict | list):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "mock-school21"})
            return

        # Profile: /services/21-school/api/v1/participants/{login}
        match_prof = re.match(r"^/services/21-school/api/v1/participants/([^/]+)$", path)
        if match_prof:
            login = match_prof.group(1)
            logger.info("Serving profile for '%s'", login)
            self._send_json(200, {
                "id": 10001,
                "login": login,
                "email": f"{login}@student.21-school.ru",
                "avatarUrl": "https://avatar.test/student.png",
                "campus": {"id": 1, "name": "Tashkent"},
                "parallel": {"id": 1, "name": "Core Program"}
            })
            return

        # Workstation: /services/21-school/api/v1/participants/{login}/workstation
        match_ws = re.match(r"^/services/21-school/api/v1/participants/([^/]+)/workstation$", path)
        if match_ws:
            login = match_ws.group(1)
            logger.info("Serving workstation for '%s'", login)
            self._send_json(200, {
                "clusterId": 1,
                "clusterName": "tillakori",
                "row": "j",
                "number": 5
            })
            return

        # Skills: /services/21-school/api/v1/participants/{login}/skills
        match_skills = re.match(r"^/services/21-school/api/v1/participants/([^/]+)/skills$", path)
        if match_skills:
            login = match_skills.group(1)
            logger.info("Serving skills for '%s'", login)
            self._send_json(200, [
                {"name": "Algorithms", "level": 5},
                {"name": "Unix", "level": 4}
            ])
            return

        # Projects: /services/21-school/api/v1/participants/{login}/projects
        match_proj = re.match(r"^/services/21-school/api/v1/participants/([^/]+)/projects$", path)
        if match_proj:
            login = match_proj.group(1)
            logger.info("Serving projects for '%s'", login)
            self._send_json(200, [
                {"name": "ft_transcendence", "status": "APPROVED"}
            ])
            return

        self._send_json(404, {"error": "Not Found", "path": path})

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

        # Keycloak token endpoint
        if path.endswith("/protocol/openid-connect/token"):
            username = payload.get("username", "synthetic_user")
            grant_type = payload.get("grant_type", "password")
            logger.info("Keycloak grant_type='%s' for username='%s'", grant_type, username)
            self._send_json(200, {
                "access_token": f"mock-s21-jwt-for-{username}",
                "refresh_token": f"mock-s21-refresh-for-{username}",
                "token_type": "Bearer",
                "expires_in": 3600
            })
            return

        self._send_json(404, {"error": "Not Found", "path": path})

    def log_message(self, format, *args):
        pass


def run(port: int = 8081):
    server = ThreadingHTTPServer(("0.0.0.0", port), MockSchool21Handler)
    logger.info("Mock School 21 server listening on 0.0.0.0:%d", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping mock server...")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    run(port)

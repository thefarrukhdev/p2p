"""Async httpx client for the School21 API.

Tasdiqlangan haqiqiy endpointlar (p2p loyihasidan):
  Auth:    POST https://auth.21-school.ru/auth/realms/EduPowerKeycloak/protocol/openid-connect/token
  Profile: GET  {API_BASE}/participants/{login}
  Skills:  GET  {API_BASE}/participants/{login}/skills
  Projects:GET  {API_BASE}/participants/{login}/projects?status=...  (taxminiy)

XP, Level, Peer Points, Peer Coins — School21 dan OLINMAYDI.
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

KEYCLOAK_TOKEN_URL = (
    "https://auth.21-school.ru/auth/realms/EduPowerKeycloak"
    "/protocol/openid-connect/token"
)


def get_keycloak_token_url() -> str:
    return getattr(settings, "KEYCLOAK_TOKEN_URL", "") or KEYCLOAK_TOKEN_URL

KEYCLOAK_CLIENT_ID = "s21-open-api"

# WAF oldidagi proxy bot user-agent larni bloklaydi.
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class School21Client:
    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url or settings.SCHOOL21_API_BASE
        self._api_client: httpx.AsyncClient | None = None
        self._auth_client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        headers = {"User-Agent": _BROWSER_UA}
        if self._api_client is None:
            self._api_client = httpx.AsyncClient(
                base_url=self._base_url, headers=headers, timeout=15.0
            )
        if self._auth_client is None:
            self._auth_client = httpx.AsyncClient(headers=headers, timeout=15.0)

    async def stop(self) -> None:
        for c in (self._api_client, self._auth_client):
            if c is not None:
                await c.aclose()
        self._api_client = None
        self._auth_client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._api_client is None:
            raise RuntimeError("School21Client not started")
        return self._api_client

    @property
    def auth_client(self) -> httpx.AsyncClient:
        if self._auth_client is None:
            raise RuntimeError("School21Client not started")
        return self._auth_client

    # ── Authentication ────────────────────────────────────────────────────────

    async def login(self, login: str, password: str) -> dict[str, Any]:
        """Keycloak password grant — access_token, refresh_token qaytaradi."""
        resp = await self.auth_client.post(
            get_keycloak_token_url(),
            data={
                "client_id": KEYCLOAK_CLIENT_ID,
                "grant_type": "password",
                "username": login,
                "password": password,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()

    async def refresh_school21_token(self, refresh_token: str) -> dict[str, Any]:
        resp = await self.auth_client.post(
            get_keycloak_token_url(),
            data={
                "client_id": KEYCLOAK_CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Profile ───────────────────────────────────────────────────────────────

    async def get_profile(self, token: str, login: str) -> dict[str, Any]:
        """GET /participants/{login} — asosiy profil ma'lumotlari."""
        resp = await self.client.get(
            f"/participants/{login}",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_location(self, token: str, login: str) -> dict[str, Any]:
        """GET /participants/{login}/workstation
        
        Returns: {clusterId, clusterName, row, number}
        Formatted as: "tillakori j5"
        """
        try:
            resp = await self.client.get(
                f"/participants/{login}/workstation",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code in (404, 204):
                return {}
            resp.raise_for_status()
            data = resp.json()
            # Format: "tillakori j5"
            cluster = data.get("clusterName", "")
            row = data.get("row", "")
            number = data.get("number", "")
            if cluster:
                data["formatted"] = f"{cluster} {row}{number}".strip()
            return data
        except httpx.HTTPStatusError:
            return {}
        except Exception:
            return {}

    # ── Projects ──────────────────────────────────────────────────────────────

    async def get_projects(
        self,
        token: str,
        status_filter: str | None = None,
        login: str | None = None,
    ) -> list[dict[str, Any]]:
        """GET /participants/{login}/projects — pagination bilan barcha loyihalar.

        status_filter: API parametri sifatida yuboriladi, lekin ishlamasligi mumkin.
        Shuning uchun natijani qaytarishdan oldin qo'shimcha filtr qilinmaydi —
        detect_main_track o'zi filtr qiladi.
        """
        if not login:
            raise ValueError("login required for get_projects")

        # Redis cache — teachable/in-progress endpointlari bir vaqtda chaqiradi;
        # School21 ni takroran hammalab 429 olmaslik uchun natijani cache qilamiz.
        import json
        from app.services.cache import redis_client
        cache_key = f"s21:projects:{login}"
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        all_projects: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, Any] = {"offset": offset, "limit": 50}
            if status_filter:
                params["statusList"] = status_filter
            try:
                resp = await self.client.get(
                    f"/participants/{login}/projects",
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except Exception as exc:
                logger.warning("S21 projects so'rovi xato (%s) — qisman qaytarilmoqda (%d ta)", exc, len(all_projects))
                break
            if resp.status_code in (404, 400):
                break
            if resp.status_code == 429:
                logger.warning("S21 429 rate-limit (projects) — qisman natija (%d ta)", len(all_projects))
                break
            try:
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                logger.warning("S21 projects HTTP %s — qisman qaytarilmoqda", resp.status_code)
                break
            data = resp.json()
            projects = data.get("projects", []) if isinstance(data, dict) else data
            if not projects:
                break
            all_projects.extend(projects)
            if len(projects) < 50:
                break
            offset += 50

        # Natijani 5 daqiqa cache qilamiz (qisman bo'lsa ham — qayta hammalashning oldini oladi).
        try:
            await redis_client.setex(cache_key, 300, json.dumps(all_projects))
        except Exception:
            pass
        return all_projects

    # ── Skills ────────────────────────────────────────────────────────────────

    async def get_skills(self, token: str, login: str) -> dict[str, Any]:
        """GET /participants/{login}/skills"""
        resp = await self.client.get(
            f"/participants/{login}/skills",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()

    async def get_coalition(self, token: str, login: str) -> dict[str, Any]:
        """GET /participants/{login}/coalition — agar mavjud bo'lsa."""
        try:
            resp = await self.client.get(
                f"/participants/{login}/coalition",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            return {}


# ── main_track detection ──────────────────────────────────────────────────────

def detect_main_track(finished_projects: list[dict[str, Any]]) -> str | None:
    """Tugatilgan loyihalar prefiks bo'yicha asosiy yo'nalishni aniqlaydi.

    School21 da tugatilgan = status 'ACCEPTED' yoki 'FINISHED'.
    Eng ko'p takrorlangan prefiks = main_track.
    """
    if not finished_projects:
        return None

    # Tugatilgan statuslar (School21 da "ACCEPTED" = tugatilgan)
    COMPLETED_STATUSES = {"FINISHED", "ACCEPTED"}

    completed = [
        p for p in finished_projects
        if p.get("status") in COMPLETED_STATUSES
    ]
    if not completed:
        return None

    # Prefiks ajratish — raqamlarni olib tashlash (DSB1, DSB2 → DSB; C3, C6 → C)
    import re
    prefixes: list[str] = []
    for proj in completed:
        name = proj.get("title") or proj.get("name") or ""
        if "_" in name:
            raw = name.split("_", 1)[0]
        elif " " in name:
            raw = name.split(" ", 1)[0]
        elif name:
            raw = name
        else:
            continue
        # Oxiridagi raqamlarni olib tashlash: "DSB7" → "DSB", "C3" → "C", "ML10" → "ML"
        clean = re.sub(r"\d+$", "", raw)
        if clean:
            prefixes.append(clean)

    if not prefixes:
        return None

    # Eng ko'p takrorlangan prefiks = asosiy yo'nalish
    return Counter(prefixes).most_common(1)[0][0]


# Module-level singleton — app lifespan da start/stop qilinadi.
school21_client = School21Client()

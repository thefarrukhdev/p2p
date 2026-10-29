#!/usr/bin/env python3
"""Check health and uptime of Frontend (Vercel) and Backend (Render)."""
from __future__ import annotations

import html
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TARGETS = [
    {
        "name": "Frontend (Vercel)",
        "url": "https://school21-p2p.vercel.app",
        "expected_code": 200,
        "team": "Frontend",
    },
    {
        "name": "Backend (Render)",
        "url": "https://p2p-o1ex.onrender.com/health",
        "expected_code": 200,
        "team": "Backend",
    },
]


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                print("Telegram notification dispatched successfully.")
    except Exception as exc:
        print(f"Failed to deliver Telegram notification: {exc}", file=sys.stderr)


def check_target(target: dict) -> dict:
    url = target["url"]
    start = time.perf_counter()
    headers = {"User-Agent": "P2P-HealthCheck/1.0"}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "name": target["name"],
                "url": url,
                "team": target["team"],
                "status_code": response.status,
                "latency_ms": latency_ms,
                "is_ok": response.status == target["expected_code"],
                "error": None,
            }
    except urllib.error.HTTPError as err:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "name": target["name"],
            "url": url,
            "team": target["team"],
            "status_code": err.code,
            "latency_ms": latency_ms,
            "is_ok": False,
            "error": f"HTTP {err.code}: {err.reason}",
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "name": target["name"],
            "url": url,
            "team": target["team"],
            "status_code": 0,
            "latency_ms": latency_ms,
            "is_ok": False,
            "error": str(exc),
        }


def main() -> None:
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    only_alerts = os.environ.get("ONLY_ALERTS", "false").lower() == "true"

    if not bot_token or not chat_id:
        print("Missing BOT_TOKEN or CHAT_ID env vars.", file=sys.stderr)
        sys.exit(1)

    results = [check_target(t) for t in TARGETS]
    has_failure = any(not r["is_ok"] for r in results)

    # Agar server qulagan bo'lsa darhol Qizil Alert yuboramiz
    if has_failure:
        lines = [
            "🚨 <b>DIQQAT: SERVER ISHLAMAYAPTI (DOWN ALERT)!</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            "⚠️ Quyidagi serverlarda nosozlik aniqlandi:",
            "",
        ]
        for r in results:
            if not r["is_ok"]:
                lines.append(
                    f"❌ <b>{r['name']}</b> ({r['team']} Developerlar)\n"
                    f"🔗 URL: {r['url']}\n"
                    f"⚠️ Sabab: <code>{html.escape(str(r['error']))}</code>\n"
                    f"⏱ Javob vaqti: <code>{r['latency_ms']}ms</code>\n"
                )
        lines.append("<i>Iltimos, zudlik bilan server va loglarni tekshiring!</i>")
        lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
        send_telegram_message(bot_token, chat_id, "\n".join(lines))
        return

    # Agar faqat nosozlik bo'lganda yuborish rejimida bo'lmasa, umumiy holat hisobotini yuboramiz
    if not only_alerts:
        lines = [
            "🟢 <b>Serverlar Holati: Barcha Tizimlar Barqaror</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            "🌐 <b>Tizim monitoringi hisoboti:</b>",
            "",
        ]
        for r in results:
            lines.append(
                f"✅ <b>{r['name']}</b>:\n"
                f"   • Status: <code>{r['status_code']} OK</code>\n"
                f"   • Ping: <code>{r['latency_ms']}ms</code>\n"
                f"   • Link: <a href=\"{r['url']}\">{r['url']}</a>"
            )
        lines.append("")
        lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
        send_telegram_message(bot_token, chat_id, "\n".join(lines))


if __name__ == "__main__":
    main()

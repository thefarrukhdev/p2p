#!/usr/bin/env python3
"""Send GitHub event notifications to Telegram."""
from __future__ import annotations

import html
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    """Send HTML-formatted text to Telegram."""
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
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status == 200:
                print("Notification sent successfully to Telegram.")
            else:
                print(f"Warning: Telegram returned status {response.status}")
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8", errors="replace")
        print(f"Telegram HTTPError: {err.code} {err.reason} - {error_body}", file=sys.stderr)
    except Exception as exc:
        print(f"Failed to send Telegram message: {exc}", file=sys.stderr)


def format_push(event: dict) -> str | None:
    repo = html.escape(event.get("repository", {}).get("full_name", "thefarrukhdev/p2p"))
    ref = event.get("ref", "")
    branch = html.escape(ref.split("/")[-1] if "/" in ref else ref)
    pusher = html.escape(
        event.get("pusher", {}).get("name")
        or event.get("sender", {}).get("login", "Noma'lum")
    )
    commits = event.get("commits", [])
    compare_url = event.get("compare", "")
    created = event.get("created", False)
    deleted = event.get("deleted", False)

    if deleted:
        return (
            f"🗑 <b>GitHub: Branch O'chirildi</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Repo:</b> <code>{repo}</code>\n"
            f"🌿 <b>Branch:</b> <code>{branch}</code>\n"
            f"👤 <b>Foydalanuvchi:</b> {pusher}\n"
        )

    if not commits and not created:
        return None

    lines = [
        f"🐙 <b>GitHub: Yangi Push</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📦 <b>Repo:</b> <code>{repo}</code>",
        f"🌿 <b>Branch:</b> <code>{branch}</code>",
        f"👤 <b>Muallif:</b> <b>{pusher}</b>",
        "",
        f"📝 <b>Commitlar ({len(commits)}):</b>",
    ]

    for c in commits[:8]:
        sha = c.get("id", "")[:7]
        msg = c.get("message", "").strip().split("\n")[0]
        c_url = c.get("url", "")
        author = html.escape(c.get("author", {}).get("name", ""))
        safe_msg = html.escape(msg)
        if c_url:
            lines.append(f"• <a href=\"{c_url}\"><code>{sha}</code></a>: {safe_msg} <i>({author})</i>")
        else:
            lines.append(f"• <code>{sha}</code>: {safe_msg}")

    if len(commits) > 8:
        lines.append(f"<i>... va yana {len(commits) - 8} ta commit</i>")

    if compare_url:
        lines.append("")
        lines.append(f"🔍 <a href=\"{compare_url}\">O'zgarishlarni ko'rish (Diff)</a>")

    lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return "\n".join(lines)


def format_pull_request(event: dict) -> str:
    repo = html.escape(event.get("repository", {}).get("full_name", "thefarrukhdev/p2p"))
    action = event.get("action", "")
    pr = event.get("pull_request", {})
    pr_num = pr.get("number", "")
    pr_title = html.escape(pr.get("title", ""))
    pr_url = pr.get("html_url", "")
    user = html.escape(pr.get("user", {}).get("login", "Noma'lum"))
    merged = pr.get("merged", False)
    base = html.escape(pr.get("base", {}).get("ref", "main"))
    head = html.escape(pr.get("head", {}).get("ref", ""))

    status_icon = "🔀"
    status_text = f"PR #{pr_num} {action.capitalize()}"

    if action == "closed":
        if merged:
            status_icon = "🟣"
            status_text = f"PR #{pr_num} Muvaffaqiyatli Birlashtirildi (Merged)!"
        else:
            status_icon = "⚪️"
            status_text = f"PR #{pr_num} Yopildi (Birlashtirilmadi)"
    elif action == "opened":
        status_icon = "🟢"
        status_text = f"Yangi PR #{pr_num} Ochildi"

    lines = [
        f"{status_icon} <b>GitHub: {status_text}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📦 <b>Repo:</b> <code>{repo}</code>",
        f"📌 <b>Sarlavha:</b> {pr_title}",
        f"👤 <b>Muallif:</b> @{user}",
        f"🔄 <b>Yo'nalish:</b> <code>{head}</code> ➔ <code>{base}</code>",
    ]

    if pr_url:
        lines.append("")
        lines.append(f"🔗 <a href=\"{pr_url}\">Pull Requestni ochish</a>")

    lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return "\n".join(lines)


def format_deployment_status(event: dict) -> str | None:
    dep_status = event.get("deployment_status", {})
    state = dep_status.get("state", "").lower()
    deployment = event.get("deployment", {})
    environment = html.escape(deployment.get("environment", "Production"))
    target_url = dep_status.get("target_url") or dep_status.get("environment_url") or ""
    description = html.escape(dep_status.get("description", ""))
    creator = html.escape(deployment.get("creator", {}).get("login", "Vercel"))
    ref = html.escape(deployment.get("ref", "main"))

    # Faqat yakuniy yoki muhim holatlarni yuboramiz (shovqin bo'lmasligi uchun)
    if state == "success":
        icon = "🚀"
        title = f"Vercel: Deployment Muvaffaqiyatli! ({environment})"
    elif state in ("failure", "error"):
        icon = "❌"
        title = f"Vercel: Deployment Xatolik Bilan Tugadi! ({environment})"
    elif state == "in_progress":
        icon = "⏳"
        title = f"Vercel: Deployment Jarayonda... ({environment})"
    else:
        return None

    lines = [
        f"{icon} <b>{title}</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🌐 <b>Muhit:</b> <code>{environment}</code>",
        f"🌿 <b>Branch:</b> <code>{ref}</code>",
        f"👤 <b>Trigger:</b> @{creator}",
    ]

    if description:
        lines.append(f"📝 <b>Tavsif:</b> {description}")

    if target_url:
        lines.append(f"🔗 <b>Sayt Havolasi:</b> <a href=\"{target_url}\">{target_url}</a>")

    lines.append(f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return "\n".join(lines)


def main() -> None:
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    event_name = os.environ.get("EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not bot_token or not chat_id:
        print("BOT_TOKEN or CHAT_ID is missing. Skipping notification.")
        return

    if not event_path or not os.path.exists(event_path):
        print(f"Event file not found at {event_path}. Sending fallback notification.")
        text = f"ℹ️ <b>GitHub Action:</b> <code>{html.escape(event_name)}</code> hodisasi ishga tushirildi."
        send_telegram_message(bot_token, chat_id, text)
        return

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    msg = None
    if event_name == "push":
        msg = format_push(event)
    elif event_name == "pull_request":
        msg = format_pull_request(event)
    elif event_name == "deployment_status":
        msg = format_deployment_status(event)
    elif event_name == "workflow_dispatch":
        msg = (
            f"⚡️ <b>GitHub Actions: Test Xabari</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 <b>Repo:</b> <code>{html.escape(event.get('repository', {}).get('full_name', 'p2p'))}</code>\n"
            f"👤 <b>Bajaruvchi:</b> {html.escape(event.get('sender', {}).get('login', 'Admin'))}\n"
            f"✅ Telegram bot aloqasi muvaffaqiyatli ishlamoqda!\n"
            f"🕒 <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
        )
    else:
        print(f"Unhandled event: {event_name}")
        return

    if msg:
        send_telegram_message(bot_token, chat_id, msg)


if __name__ == "__main__":
    main()

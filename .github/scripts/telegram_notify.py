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
            f"❌ <b>[GitHub] Branch O'chirildi</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Repo: <code>{repo}</code>\n"
            f"Branch: <code>{branch}</code>\n"
            f"Foydalanuvchi: {pusher}\n"
        )

    if not commits and not created:
        return None

    lines = [
        f"<b>[GitHub] Yangi Push</b>",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Repo: <code>{repo}</code>",
        f"Branch: <code>{branch}</code>",
        f"Muallif: <b>{pusher}</b>",
        "",
        f"Commitlar ({len(commits)}):",
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
        lines.append(f"Diff: <a href=\"{compare_url}\">O'zgarishlarni ko'rish</a>")

    lines.append(f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
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

    if action == "closed":
        if merged:
            header = f"✅ <b>[GitHub] PR #{pr_num} Birlashtirildi (Merged)</b>"
        else:
            header = f"❌ <b>[GitHub] PR #{pr_num} Yopildi</b>"
    elif action == "opened":
        header = f"<b>[GitHub] Yangi PR #{pr_num} Ochildi</b>"
    else:
        header = f"<b>[GitHub] PR #{pr_num} {action.capitalize()}</b>"

    lines = [
        header,
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Repo: <code>{repo}</code>",
        f"Sarlavha: {pr_title}",
        f"Muallif: @{user}",
        f"Yo'nalish: <code>{head}</code> ➔ <code>{base}</code>",
    ]

    if pr_url:
        lines.append("")
        lines.append(f"Havola: <a href=\"{pr_url}\">Pull Requestni ochish</a>")

    lines.append(f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return "\n".join(lines)


def fetch_vercel_build_logs(token: str) -> list[str]:
    """Fetch the latest Vercel build log events via API."""
    try:
        url = "https://api.vercel.com/v6/deployments?projectId=prj_gvSNNdflPJB5Vqydo4iR5McuoB30&limit=1"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            dep_id = data["deployments"][0]["uid"]

        events_url = f"https://api.vercel.com/v2/deployments/{dep_id}/events?limit=40"
        req = urllib.request.Request(events_url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            events = json.loads(r.read().decode())
            logs = []
            for ev in events:
                payload = ev.get("payload", {})
                text = payload.get("text")
                if text:
                    logs.append(text)
            return logs[-8:]
    except Exception:
        return []


def format_deployment_status(event: dict, vercel_token: str | None = None) -> str | None:
    dep_status = event.get("deployment_status", {})
    state = dep_status.get("state", "").lower()
    deployment = event.get("deployment", {})
    environment = html.escape(deployment.get("environment", "Production"))
    target_url = dep_status.get("target_url") or dep_status.get("environment_url") or ""
    description = html.escape(dep_status.get("description", ""))
    creator = html.escape(deployment.get("creator", {}).get("login", "Vercel"))
    ref = html.escape(deployment.get("ref", "main"))

    if state == "success":
        title = f"✅ <b>[Vercel] Deployment Muvaffaqiyatli ({environment})</b>"
    elif state in ("failure", "error"):
        title = f"❌ <b>[Vercel] Deploymentda Xatolik ({environment})</b>"
    elif state == "in_progress":
        title = f"<b>[Vercel] Deployment Jarayonda ({environment})</b>"
    else:
        return None

    lines = [
        title,
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Muhit: <code>{environment}</code>",
        f"Branch: <code>{ref}</code>",
        f"Trigger: @{creator}",
    ]

    if description:
        lines.append(f"Tavsif: {description}")

    if target_url:
        lines.append(f"Sayt: <a href=\"{target_url}\">{target_url}</a>")

    if state in ("failure", "error") and vercel_token:
        logs = fetch_vercel_build_logs(vercel_token)
        if logs:
            lines.extend([
                "",
                "<b>Vercel Build Loglari:</b>",
                f"<pre>{html.escape(chr(10).join(logs))}</pre>"
            ])

    lines.append(f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>")
    return "\n".join(lines)


def main() -> None:
    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    vercel_token = os.environ.get("VERCEL_TOKEN")
    event_name = os.environ.get("EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")

    if not bot_token or not chat_id:
        print("BOT_TOKEN or CHAT_ID is missing. Skipping notification.")
        return

    if not event_path or not os.path.exists(event_path):
        print(f"Event file not found at {event_path}. Sending fallback notification.")
        text = f"<b>[GitHub Actions]</b> <code>{html.escape(event_name)}</code> hodisasi ishga tushirildi."
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
        msg = format_deployment_status(event, vercel_token)
    elif event_name == "workflow_dispatch":
        msg = (
            f"✅ <b>[GitHub Actions] Test Xabari</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Repo: <code>{html.escape(event.get('repository', {}).get('full_name', 'p2p'))}</code>\n"
            f"Bajaruvchi: {html.escape(event.get('sender', {}).get('login', 'Admin'))}\n"
            f"Telegram bot aloqasi muvaffaqiyatli ishlamoqda.\n"
            f"Vaqt: <code>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</code>"
        )
    else:
        print(f"Unhandled event: {event_name}")
        return

    if msg:
        send_telegram_message(bot_token, chat_id, msg)


if __name__ == "__main__":
    main()

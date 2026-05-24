from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

CONNPASS_ENDPOINT = "https://connpass.com/api/v2/events/"
DEFAULT_SUBDOMAIN = "kaira-thesis-reading"
DEFAULT_TIMEZONE = "Asia/Tokyo"
USER_AGENT = "kaira-event-reminder/0.1 (+https://github.com/)"
GOOGLE_MEET_URL_PATTERN = re.compile(r"https?://meet\.google\.com/[a-z0-9-]+", re.IGNORECASE)
READING_EVENT_KEYWORD = "輪読会"
READING_WEBHOOK_ENV = "SLACK_WEBHOOK_URL_EVENT_READING"
TECH_WEBHOOK_ENV = "SLACK_WEBHOOK_URL_EVENT_TECH"


@dataclass(frozen=True)
class Event:
    title: str
    place: str
    url: str
    started_at: datetime
    meet_url: str | None = None


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def request_text(url: str, headers: dict[str, str], payload: dict[str, Any] | None = None) -> str:
    data = None
    method = "GET"
    request_headers = dict(headers)

    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers["Content-Type"] = "application/json; charset=utf-8"
        method = "POST"

    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {error_body}") from error
    except URLError as error:
        raise RuntimeError(f"Failed to request {url}: {error.reason}") from error


def request_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    body = request_text(url, headers)

    if not body:
        return {}
    return json.loads(body)


def fetch_today_events(api_key: str, subdomain: str, today: datetime, tz: ZoneInfo) -> list[Event]:
    target_date = today.date()
    query = urlencode(
        {
            "subdomain": subdomain,
            "ymd": target_date.strftime("%Y%m%d"),
            "order": "1",
            "count": "100",
        }
    )
    url = f"{CONNPASS_ENDPOINT}?{query}"
    data = request_json(
        url,
        {
            "X-API-Key": api_key,
            "User-Agent": USER_AGENT,
        },
    )

    events: list[Event] = []
    for item in data.get("events", []):
        started_at = parse_datetime(item.get("started_at"), tz)
        if started_at.date() != target_date:
            continue

        event_url = item.get("event_url") or item.get("url") or ""
        if not event_url and item.get("event_id"):
            event_url = f"https://connpass.com/event/{item['event_id']}/"

        events.append(
            Event(
                title=item.get("title") or "(タイトル未設定)",
                place=format_place(item),
                url=event_url,
                started_at=started_at,
                meet_url=extract_google_meet_url(item.get("description") or ""),
            )
        )

    return sorted(events, key=lambda event: event.started_at)


def parse_datetime(value: str | None, tz: ZoneInfo) -> datetime:
    if not value:
        raise RuntimeError("connpass event is missing started_at")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def format_place(item: dict[str, Any]) -> str:
    place = (item.get("place") or "").strip()
    address = (item.get("address") or "").strip()
    if place and address and address not in place:
        return f"{place} ({address})"
    return place or address or "未定"


def extract_google_meet_url(description_html: str) -> str | None:
    description = html.unescape(description_html)
    match = GOOGLE_MEET_URL_PATTERN.search(description)
    if not match:
        return None
    return match.group(0).rstrip(").,、。")


def build_slack_text(event: Event) -> str:
    lines = [
        "<!channel>", 
        "こちら本日開催です！",
        f"- イベント名: {event.title}",
        f"- 場所: {event.place}",
        f"- connpass: {event.url}",
    ]
    if event.meet_url:
        lines.append(f"- Google Meet: {event.meet_url}")
    return "\n".join(lines)


def target_webhook_env_name(event: Event) -> str:
    if READING_EVENT_KEYWORD in event.title:
        return READING_WEBHOOK_ENV
    return TECH_WEBHOOK_ENV


def resolve_webhook_url(event: Event) -> tuple[str, str]:
    env_name = target_webhook_env_name(event)
    return require_env(env_name), env_name


def post_to_slack(webhook_url: str, text: str) -> None:
    request_text(
        webhook_url,
        {"User-Agent": USER_AGENT},
        {"text": text, "unfurl_links": True},
    )


def run(dry_run: bool = False) -> int:
    load_dotenv()

    tz = ZoneInfo(os.environ.get("TZ", DEFAULT_TIMEZONE))
    today = datetime.now(tz)
    subdomain = os.environ.get("CONNPASS_SUBDOMAIN", DEFAULT_SUBDOMAIN)
    events = fetch_today_events(require_env("CONNPASS_API_KEY"), subdomain, today, tz)

    if not events:
        print(f"No KaiRA events today ({today.date().isoformat()}).")
        return 0

    for event in events:
        text = build_slack_text(event)
        target_env_name = target_webhook_env_name(event)
        if dry_run:
            print(f"Target: {target_env_name}")
            print(text)
            print()
        else:
            webhook_url, env_name = resolve_webhook_url(event)
            post_to_slack(webhook_url, text)
            print(f"Posted to {env_name}: {event.title}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Post today's KaiRA connpass events to Slack.")
    parser.add_argument("--dry-run", action="store_true", help="Print Slack messages without posting.")
    args = parser.parse_args()

    try:
        raise SystemExit(run(dry_run=args.dry_run))
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()

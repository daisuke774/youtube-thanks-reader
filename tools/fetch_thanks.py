from __future__ import annotations

import argparse
import json
import secrets
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "public"
THANKS_DIR = PUBLIC_DIR / "thanks"
ASSETS_DIR = PUBLIC_DIR / "assets"


PAID_RENDERERS = {
    "liveChatPaidMessageRenderer": "super_chat",
    "liveChatPaidStickerRenderer": "super_sticker",
    "liveChatMembershipItemRenderer": "milestone",
}


@dataclass
class ThanksItem:
    sent_at: str
    time: str
    author_name: str
    kind: str
    amount: float | None
    currency: str
    amount_text: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sent_at": self.sent_at,
            "time": self.time,
            "author_name": self.author_name,
            "kind": self.kind,
            "amount": self.amount,
            "currency": self.currency,
            "amount_text": self.amount_text,
            "message": self.message,
        }


def simple_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "simpleText" in value:
            return str(value["simpleText"])
        if "runs" in value:
            parts = []
            for run in value["runs"]:
                if "text" in run:
                    parts.append(str(run["text"]))
                elif "emoji" in run:
                    emoji = run["emoji"]
                    parts.append(emoji.get("shortcuts", [""])[0] or emoji.get("emojiId", ""))
            return "".join(parts)
    return ""


def find_renderers(node: Any) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in PAID_RENDERERS and isinstance(value, dict):
                found.append((key, value))
            else:
                found.extend(find_renderers(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(find_renderers(item))
    return found


def timestamp_to_datetime(renderer: dict[str, Any], tz_name: str) -> tuple[str, str]:
    tz = ZoneInfo(tz_name)
    timestamp_usec = renderer.get("timestampUsec")
    if timestamp_usec:
        dt = datetime.fromtimestamp(int(timestamp_usec) / 1_000_000, tz=timezone.utc).astimezone(tz)
    else:
        dt = datetime.now(tz)
    return dt.isoformat(), dt.strftime("%H:%M")


def parse_amount(amount_text: str) -> tuple[float | None, str]:
    if not amount_text:
        return None, ""
    compact = amount_text.replace(",", "").replace("\u00a0", " ").strip()
    currency = ""
    number_chars = []
    for char in compact:
        if char.isdigit() or char == ".":
            number_chars.append(char)
        elif not number_chars and not char.isspace():
            currency += char
    try:
        amount = float("".join(number_chars)) if number_chars else None
    except ValueError:
        amount = None
    return amount, currency


def renderer_to_item(renderer_name: str, renderer: dict[str, Any], tz_name: str) -> ThanksItem:
    kind = PAID_RENDERERS[renderer_name]
    sent_at, time_label = timestamp_to_datetime(renderer, tz_name)
    author = simple_text(renderer.get("authorName")) or simple_text(renderer.get("authorExternalChannelId"))
    amount_text = simple_text(renderer.get("purchaseAmountText"))
    amount, currency = parse_amount(amount_text)

    message = simple_text(renderer.get("message"))
    if kind == "super_sticker" and not message:
        message = simple_text(renderer.get("sticker", {}).get("accessibility", {}).get("accessibilityData", {}).get("label"))
    if kind == "milestone" and not message:
        message = simple_text(renderer.get("headerSubtext")) or simple_text(renderer.get("headerPrimaryText"))

    return ThanksItem(
        sent_at=sent_at,
        time=time_label,
        author_name=author or "ユーザー名",
        kind=kind,
        amount=amount,
        currency=currency,
        amount_text=amount_text,
        message=message,
    )


def parse_live_chat_json(path: Path, tz_name: str) -> list[ThanksItem]:
    items: list[ThanksItem] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            for renderer_name, renderer in find_renderers(payload):
                items.append(renderer_to_item(renderer_name, renderer, tz_name))
    items.sort(key=lambda item: item.sent_at)
    return items


def run_yt_dlp(url: str) -> tuple[Path, dict[str, Any]]:
    if not shutil.which("yt-dlp"):
        raise RuntimeError("yt-dlp が見つかりません。python -m pip install yt-dlp を実行してください。")

    tmp_dir = Path(tempfile.mkdtemp(prefix="thanks-chat-"))
    output_tpl = str(tmp_dir / "%(id)s.%(ext)s")
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-info-json",
        "--write-subs",
        "--sub-langs",
        "live_chat",
        "--sub-format",
        "json",
        "-o",
        output_tpl,
        url,
    ]
    subprocess.run(command, check=True)

    chat_files = list(tmp_dir.glob("*.live_chat.json")) + list(tmp_dir.glob("*.live_chat.*.json"))
    if not chat_files:
        all_json = list(tmp_dir.glob("*.json"))
        chat_files = [path for path in all_json if "live_chat" in path.name]
    if not chat_files:
        raise RuntimeError("live_chat JSONが保存されませんでした。配信URLまたはチャットリプレイの有無を確認してください。")

    info_files = [path for path in tmp_dir.glob("*.info.json")]
    info: dict[str, Any] = {}
    if info_files:
        info = json.loads(info_files[0].read_text(encoding="utf-8"))
    return chat_files[0], info


def demo_items(tz_name: str) -> tuple[list[ThanksItem], dict[str, Any]]:
    tz = ZoneInfo(tz_name)
    base = datetime(2026, 6, 12, 20, 13, tzinfo=tz)
    rows = [
        (0, "super_chat", "¥500", "Aoi", "いつも楽しい配信ありがとうございます！"),
        (12, "super_chat", "¥1,000", "Haruka", "アーカイブ勢ですが応援しています。"),
        (28, "milestone", "", "Mika", "メンバー12か月になりました。これからも楽しみです。"),
        (43, "super_sticker", "¥320", "Ren", "Super Sticker"),
    ]
    items = []
    for minutes, kind, amount_text, author, message in rows:
        dt = base.replace(minute=base.minute + minutes)
        amount, currency = parse_amount(amount_text)
        items.append(
            ThanksItem(
                sent_at=dt.isoformat(),
                time=dt.strftime("%H:%M"),
                author_name=author,
                kind=kind,
                amount=amount,
                currency=currency,
                amount_text=amount_text,
                message=message,
            )
        )
    return items, {"title": "サンプル配信"}


def page_html() -> str:
    return """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Thanks Reader</title>
  <link rel="stylesheet" href="../../assets/styles.css">
</head>
<body>
  <div class="app-shell">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="title-block">
          <h1 class="app-title" data-title>Thanks Reader</h1>
          <p class="meta-line" data-meta></p>
        </div>
        <div class="toolbar">
          <button class="text-button primary" type="button" data-open-reader>読み上げ</button>
        </div>
      </div>
    </header>
    <main class="content">
      <section class="event-list" data-list aria-label="Thanks list"></section>
    </main>
  </div>

  <section class="reader" data-reader aria-hidden="true">
    <div class="reader-header">
      <span class="reader-count" data-count></span>
      <button class="icon-button" type="button" data-close-reader aria-label="閉じる">×</button>
    </div>
    <article class="reader-card" data-reader-card>
      <div class="reader-time" data-reader-time></div>
      <div class="reader-kind" data-reader-kind></div>
      <div class="reader-author" data-reader-author></div>
      <div class="reader-amount" data-reader-amount></div>
      <div class="reader-message" data-reader-message></div>
    </article>
    <div class="reader-footer">
      <div class="reader-nav">
        <button class="text-button" type="button" data-prev>前へ</button>
        <button class="text-button primary" type="button" data-next>次へ</button>
      </div>
    </div>
  </section>
  <script src="../../assets/app.js"></script>
</body>
</html>
"""


def write_page(page_id: str, items: list[ThanksItem], info: dict[str, Any], source_url: str | None) -> Path:
    page_dir = THANKS_DIR / page_id
    page_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "meta": {
            "id": page_id,
            "page_title": "お礼読み上げ",
            "video_title": info.get("title", ""),
            "source_url": source_url or "",
            "created_at": now,
            "schema_version": 1,
        },
        "items": [item.to_dict() for item in items],
    }
    (page_dir / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (page_dir / "index.html").write_text(page_html(), encoding="utf-8")
    return page_dir


def git_push(page_dir: Path, message: str) -> None:
    paths = [str(page_dir.relative_to(ROOT)), "public/robots.txt", "public/assets/app.js", "public/assets/styles.css"]
    subprocess.run(["git", "add", *paths], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    subprocess.run(["git", "push"], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube thanks reader page generator")
    parser.add_argument("url", nargs="?", help="YouTube配信URL")
    parser.add_argument("--id", dest="page_id", help="公開URLに使うID。省略時はランダム生成")
    parser.add_argument("--timezone", default="Asia/Tokyo", help="表示時刻のタイムゾーン")
    parser.add_argument("--demo", action="store_true", help="サンプルデータでページを生成")
    parser.add_argument("--push", action="store_true", help="生成後にGitHubへpush")
    args = parser.parse_args()

    if not args.demo and not args.url:
        parser.error("YouTube配信URL、または --demo が必要です。")

    page_id = args.page_id or secrets.token_urlsafe(18).replace("-", "").replace("_", "")

    if args.demo:
        items, info = demo_items(args.timezone)
        source_url = None
    else:
        chat_file, info = run_yt_dlp(args.url)
        items = parse_live_chat_json(chat_file, args.timezone)
        source_url = args.url

    page_dir = write_page(page_id, items, info, source_url)
    if args.push:
        git_push(page_dir, f"Add thanks page {page_id}")

    print(f"Generated: {page_dir}")
    print(f"URL path: /thanks/{page_id}/")
    print(f"Items: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

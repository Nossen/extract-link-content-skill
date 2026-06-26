#!/usr/bin/env python3
"""Normalize extracted link content into scored material cards.

The script is intentionally dependency-free so a Codex skill can use it in a
fresh local environment. It accepts common OpenCLI JSON shapes plus the compact
extraction report described by the skill.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "material-card-v1"
DEFAULT_LIBRARY = "~/Documents/link-content-materials/materials.jsonl"


PLATFORM_PATTERNS = {
    "x": ["x.com", "twitter.com"],
    "youtube": ["youtube.com", "youtu.be"],
    "bilibili": ["bilibili.com", "b23.tv"],
    "xiaohongshu": ["xiaohongshu.com", "xhslink.com"],
    "douyin": ["douyin.com", "iesdouyin.com"],
    "reddit": ["reddit.com", "redd.it"],
}

HOOK_TERMS = [
    "why",
    "how",
    "what",
    "secret",
    "mistake",
    "guide",
    "tutorial",
    "full",
    "best",
    "worst",
    "为什么",
    "怎么",
    "如何",
    "教程",
    "攻略",
    "避坑",
    "全流程",
    "秘诀",
    "真相",
    "爆款",
    "排名",
    "排行榜",
    "复盘",
]

RISK_TERMS = [
    "完整版",
    "全集",
    "搬运",
    "转载",
    "盗版",
    "电影",
    "音乐",
    "official video",
    "full song",
    "copyright",
]

TOPIC_SPLIT_RE = re.compile(r"[\s,，、;；|/#]+")

ZH_FIELD_LABELS = {
    "written": "是否写入",
    "action": "写入动作",
    "library": "素材库路径",
    "material_id": "素材ID",
    "duplicate": "是否重复",
    "duplicate_of": "重复来源ID",
    "score": "评分",
    "card": "素材卡",
    "schema_version": "结构版本",
    "source_url": "来源链接",
    "canonical_url": "规范链接",
    "platform": "平台",
    "content_type": "内容类型",
    "title": "标题",
    "author": "作者",
    "published_at": "发布时间",
    "captured_at": "抓取时间",
    "language": "语言",
    "text": "文本内容",
    "body": "正文",
    "transcript": "字幕逐字稿",
    "comments": "评论",
    "media": "媒体",
    "metrics": "互动数据",
    "likes": "点赞数",
    "shares": "分享数",
    "views": "播放量",
    "collects": "收藏数",
    "tags": "标签",
    "signals": "素材信号",
    "hook": "标题钩子",
    "topics": "主题",
    "reuse_angles": "复用角度",
    "pain_points": "痛点",
    "risk_flags": "风险标记",
    "scores": "评分明细",
    "topic_value": "选题价值",
    "hook_strength": "钩子强度",
    "adaptability": "改编潜力",
    "discussion_potential": "讨论潜力",
    "account_fit": "账号匹配度",
    "risk": "风险分",
    "total": "总分",
    "dedupe": "去重信息",
    "content_hash": "内容哈希",
    "is_duplicate": "是否重复",
    "extraction": "抓取信息",
    "tool_used": "使用工具",
    "confidence": "置信度",
    "blockers": "阻塞点",
    "type": "类型",
    "url": "链接",
    "role": "用途",
    "poster": "封面",
}

ZH_VALUE_LABELS = {
    "appended": "已追加",
    "replaced": "已刷新",
    "duplicate": "重复未写入",
    "video": "视频",
    "image": "图片",
    "article": "文章",
    "text": "文本",
    "external": "外链",
    "thumbnail": "缩略图",
    "preview_image_url": "预览图",
    "poster": "封面",
    "cover": "封面",
    "external_media_link": "外部媒体链接",
    "turn into a step-by-step tutorial": "改写成分步教程",
    "turn into a mistake/avoidance post": "改写成避坑内容",
    "turn into a comparison or ranking": "改写成对比或排行",
    "turn into a case-study breakdown": "改写成案例拆解",
    "turn into a topic explainer": "改写成主题解释",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_body_text(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return ""
    return clean_text(value)


def normalize_date_text(value: Any) -> str:
    text = clean_text(value)
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def localize_display(value: Any, lang: str) -> Any:
    if lang == "en":
        return value
    if isinstance(value, dict):
        localized: dict[str, Any] = {}
        for key, item in value.items():
            localized[ZH_FIELD_LABELS.get(str(key), str(key))] = localize_display(item, lang)
        return localized
    if isinstance(value, list):
        return [localize_display(item, lang) for item in value]
    if isinstance(value, str):
        return ZH_VALUE_LABELS.get(value, value)
    return value


def print_display_json(value: Any, lang: str) -> None:
    print(json.dumps(localize_display(value, lang), ensure_ascii=False, indent=2))


def read_json(path: str | None) -> Any:
    if not path or path == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(path).read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    return json.loads(raw)


def load_profile(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    profile_path = Path(path).expanduser()
    if not profile_path.exists():
        raise SystemExit(f"profile not found: {profile_path}")
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("profile must be a JSON object")
    return data


def field_table_to_dict(items: list[Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        field = item.get("field")
        if field is None:
            continue
        fields[str(field).strip().lower()] = item.get("value")
    return fields


def first_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
        return {}
    return value if isinstance(value, dict) else {}


def infer_platform(url: str, explicit: str = "") -> str:
    if explicit:
        return explicit.lower()
    lower = url.lower()
    for platform, needles in PLATFORM_PATTERNS.items():
        if any(needle in lower for needle in needles):
            return platform
    return "unknown"


def infer_content_type(source: dict[str, Any], text: str, media: list[dict[str, Any]]) -> str:
    raw_type = clean_text(
        source.get("content_type")
        or source.get("type")
        or source.get("post_hint")
        or source.get("media_kind")
    ).lower()
    source_url = clean_text(source.get("source_url") or source.get("url") or source.get("webpage_url")).lower()
    if "video" in raw_type:
        return "video"
    if "image" in raw_type or "photo" in raw_type:
        return "image"
    if source.get("bvid") or "/video/" in source_url or "youtube.com/watch" in source_url or "youtu.be/" in source_url:
        return "video"
    if source.get("transcript") or "subtitle" in raw_type:
        return "video"
    if any(item.get("type") == "video" for item in media):
        return "video"
    if any(item.get("type") == "image" for item in media):
        return "image"
    if len(text) > 800:
        return "article"
    return "text"


def listify(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def collect_media(source: dict[str, Any]) -> list[dict[str, Any]]:
    media: list[dict[str, Any]] = []

    for raw_url in listify(source.get("media_urls")) + listify(source.get("gallery_urls")):
        url = clean_text(raw_url)
        if not url:
            continue
        media_type = "video" if re.search(r"\.(mp4|m3u8|webm)(\?|$)", url, re.I) else "image"
        media.append({"type": media_type, "url": url})

    for key in ("preview_image_url", "thumbnail", "poster", "image", "cover"):
        url = clean_text(source.get(key))
        if url and not any(item.get("url") == url for item in media):
            media.append({"type": "image", "url": url, "role": key})

    posters = listify(source.get("media_posters"))
    for index, poster in enumerate(posters):
        url = clean_text(poster)
        if url:
            if index < len(media):
                media[index]["poster"] = url
            else:
                media.append({"type": "image", "url": url, "role": "poster"})

    if source.get("url_overridden_by_dest"):
        dest = clean_text(source.get("url_overridden_by_dest"))
        if dest and dest != clean_text(source.get("url")):
            media.append({"type": "external", "url": dest})

    return media


def normalize_from_raw(raw: Any, overrides: dict[str, str]) -> dict[str, Any]:
    source: dict[str, Any]

    if isinstance(raw, list) and raw and all(isinstance(x, dict) and "field" in x for x in raw):
        source = field_table_to_dict(raw)
    elif isinstance(raw, list):
        source = first_dict(raw).copy()
        if source.get("type") == "POST":
            source.setdefault("title", source.get("text", "").split("\n", 1)[0])
            source.setdefault("body", source.get("text"))
    elif isinstance(raw, dict):
        if isinstance(raw.get("extracted_text"), dict):
            source = raw.copy()
            extracted = raw["extracted_text"]
            source.setdefault("body", extracted.get("body") or extracted.get("text"))
            source.setdefault("transcript", extracted.get("transcript"))
        else:
            source = raw.copy()
    else:
        source = {}

    source.update({k: v for k, v in overrides.items() if v})

    source_url = clean_text(
        source.get("source_url")
        or source.get("url")
        or source.get("webpage_url")
        or source.get("canonical_url")
    )
    title = clean_text(source.get("title") or source.get("desc") or source.get("description"))
    body = clean_text(
        source.get("body")
        or source.get("content")
        or source.get("text")
        or source.get("description")
        or source.get("desc")
    )
    transcript = clean_body_text(source.get("transcript") or source.get("subtitle") or source.get("subtitles"))
    author = clean_text(source.get("author") or source.get("uploader") or source.get("channel"))
    published_at = normalize_date_text(
        source.get("published_at")
        or source.get("publish_time")
        or source.get("publishdate")
        or source.get("publish_date")
        or source.get("upload_date")
        or source.get("created_at")
    )
    platform = infer_platform(source_url, clean_text(source.get("platform")))
    media = collect_media(source)
    content_text = "\n\n".join(part for part in [title, body, transcript] if part)
    content_type = infer_content_type(source, content_text, media)

    tags = extract_tags(source, content_text)
    metrics = extract_metrics(source)
    risk_flags = detect_risks(content_text, media)
    scores = score_card(content_text, metrics, tags, risk_flags, load_profile_value(source, "_profile", {}))

    content_hash = sha256_text(re.sub(r"\s+", " ", content_text.lower()).strip())
    id_basis = source_url or content_hash
    material_id = sha256_text(f"{platform}|{id_basis}")[:16]

    return {
        "schema_version": SCHEMA_VERSION,
        "material_id": material_id,
        "source_url": source_url,
        "canonical_url": source_url,
        "platform": platform,
        "content_type": content_type,
        "title": title,
        "author": author,
        "published_at": published_at,
        "captured_at": utc_now(),
        "language": clean_text(source.get("language")),
        "text": {
            "body": body,
            "transcript": transcript,
            "comments": normalize_comments(source),
        },
        "media": media,
        "metrics": metrics,
        "tags": tags,
        "signals": {
            "hook": build_hook(title, body),
            "topics": infer_topics(tags, content_text),
            "reuse_angles": infer_reuse_angles(content_text, tags),
            "pain_points": infer_pain_points(content_text),
            "risk_flags": risk_flags,
        },
        "scores": scores,
        "dedupe": {
            "content_hash": content_hash,
            "is_duplicate": False,
            "duplicate_of": "",
        },
        "extraction": {
            "tool_used": clean_text(source.get("tool_used")),
            "confidence": clean_text(source.get("confidence")),
            "blockers": listify(source.get("blockers")),
        },
    }


def load_profile_value(source: dict[str, Any], key: str, default: Any) -> Any:
    value = source.get(key, default)
    return value if value is not None else default


def extract_tags(source: dict[str, Any], text: str) -> list[str]:
    tags: list[str] = []
    for raw in listify(source.get("tags")) + listify(source.get("keywords")):
        for part in TOPIC_SPLIT_RE.split(clean_text(raw)):
            if part:
                tags.append(part.lstrip("#"))
    for match in re.findall(r"#([\w\u4e00-\u9fff-]+)", text):
        tags.append(match)
    return sorted(set(tag for tag in tags if tag))


def number_from_any(value: Any) -> int | None:
    if value is None:
        return None
    text = clean_text(value).lower()
    if not text:
        return None
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("k"):
        multiplier = 1000
        text = text[:-1]
    elif text.endswith("m"):
        multiplier = 1000000
        text = text[:-1]
    text = text.replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return int(float(match.group(0)) * multiplier)


def extract_metrics(source: dict[str, Any]) -> dict[str, int | None]:
    key_map = {
        "likes": ["likes", "like_count", "digg_count"],
        "comments": ["comments", "comment_count"],
        "shares": ["shares", "share_count"],
        "views": ["views", "view", "view_count", "plays", "play_count"],
        "collects": ["collects", "favorites", "favorite_count"],
        "score": ["score", "upvotes"],
    }
    metrics: dict[str, int | None] = {}
    for name, keys in key_map.items():
        metrics[name] = None
        for key in keys:
            parsed = number_from_any(source.get(key))
            if parsed is not None:
                metrics[name] = parsed
                break
    return metrics


def normalize_comments(source: dict[str, Any]) -> list[dict[str, Any]]:
    raw_comments = source.get("comments_or_replies") or source.get("comments") or source.get("top_comments")
    if isinstance(raw_comments, (int, float)):
        return []
    if isinstance(raw_comments, str) and number_from_any(raw_comments) is not None and len(raw_comments.strip()) <= 8:
        return []
    comments: list[dict[str, Any]] = []
    for item in listify(raw_comments):
        if isinstance(item, dict):
            text = clean_text(item.get("text") or item.get("content") or item.get("body"))
            if text:
                comments.append({
                    "author": clean_text(item.get("author")),
                    "text": text,
                    "score": number_from_any(item.get("score") or item.get("likes")),
                })
        else:
            text = clean_text(item)
            if text:
                comments.append({"author": "", "text": text, "score": None})
    return comments[:20]


def detect_risks(text: str, media: list[dict[str, Any]]) -> list[str]:
    lowered = text.lower()
    flags = [term for term in RISK_TERMS if term.lower() in lowered]
    if any(item.get("type") == "external" for item in media):
        flags.append("external_media_link")
    return sorted(set(flags))


def score_card(
    text: str,
    metrics: dict[str, int | None],
    tags: list[str],
    risk_flags: list[str],
    profile: dict[str, Any],
) -> dict[str, int]:
    normalized = text.lower()
    length = len(text)
    engagement = sum(value or 0 for value in metrics.values())
    profile_keywords = [str(x).lower() for x in profile.get("keywords", []) if str(x).strip()]
    banned_keywords = [str(x).lower() for x in profile.get("avoid_keywords", []) if str(x).strip()]

    hook_strength = 25
    if any(term.lower() in normalized for term in HOOK_TERMS):
        hook_strength += 25
    if re.search(r"[?？!！]|\d", text[:120]):
        hook_strength += 15
    hook_strength = min(hook_strength, 100)

    topic_value = 35 + min(len(tags) * 5, 25) + min(engagement // 500, 30)
    topic_value = min(topic_value, 100)

    adaptability = 30
    if 80 <= length <= 2500:
        adaptability += 25
    if tags:
        adaptability += 15
    if re.search(r"(步骤|流程|教程|方法|原因|对比|案例|how|why|guide)", normalized):
        adaptability += 20
    adaptability = min(adaptability, 100)

    discussion_potential = 25 + min((metrics.get("comments") or 0) * 2, 35)
    if re.search(r"(争议|质疑|反常识|误区|别再|不要|为什么|vs|对比)", normalized):
        discussion_potential += 25
    discussion_potential = min(discussion_potential, 100)

    account_fit = 50
    if profile_keywords:
        hits = sum(1 for keyword in profile_keywords if keyword in normalized)
        account_fit = min(100, 30 + hits * 18)
    if any(keyword in normalized for keyword in banned_keywords):
        account_fit = max(0, account_fit - 40)

    risk = min(100, len(risk_flags) * 25)
    total = round(
        topic_value * 0.24
        + hook_strength * 0.20
        + adaptability * 0.22
        + discussion_potential * 0.18
        + account_fit * 0.16
        - risk * 0.18
    )
    total = max(0, min(total, 100))

    return {
        "topic_value": topic_value,
        "hook_strength": hook_strength,
        "adaptability": adaptability,
        "discussion_potential": discussion_potential,
        "account_fit": account_fit,
        "risk": risk,
        "total": total,
    }


def build_hook(title: str, body: str) -> str:
    base = title or body
    return clean_text(base).split("\n", 1)[0][:160]


def infer_topics(tags: list[str], text: str) -> list[str]:
    topics = list(tags[:8])
    for term in HOOK_TERMS:
        if term.lower() in text.lower() and term not in topics:
            topics.append(term)
    return topics[:10]


def infer_reuse_angles(text: str, tags: list[str]) -> list[str]:
    lowered = text.lower()
    angles: list[str] = []
    if re.search(r"(教程|流程|how|guide|step)", lowered):
        angles.append("turn into a step-by-step tutorial")
    if re.search(r"(误区|避坑|mistake|wrong)", lowered):
        angles.append("turn into a mistake/avoidance post")
    if re.search(r"(对比|vs|versus|排名|排行榜|best|worst)", lowered):
        angles.append("turn into a comparison or ranking")
    if re.search(r"(案例|复盘|story|case)", lowered):
        angles.append("turn into a case-study breakdown")
    if tags and not angles:
        angles.append("turn into a topic explainer")
    return angles[:5]


def infer_pain_points(text: str) -> list[str]:
    patterns = [
        r"不会[^，。,.!?！？]{0,20}",
        r"不知道[^，。,.!?！？]{0,20}",
        r"太难[^，。,.!?！？]{0,20}",
        r"失败[^，。,.!?！？]{0,20}",
        r"成本[^，。,.!?！？]{0,20}",
        r"waste[^,.!?]{0,40}",
        r"hard[^,.!?]{0,40}",
    ]
    points: list[str] = []
    for pattern in patterns:
        points.extend(clean_text(match) for match in re.findall(pattern, text, flags=re.I))
    return [point for point in points if point][:5]


def existing_cards(library_path: Path) -> list[dict[str, Any]]:
    if not library_path.exists():
        return []
    cards: list[dict[str, Any]] = []
    with library_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                cards.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return cards


def duplicate_index(card: dict[str, Any], existing: list[dict[str, Any]]) -> int | None:
    source_url = card.get("source_url")
    content_hash = card.get("dedupe", {}).get("content_hash")
    for index, old in enumerate(existing):
        same_url = source_url and source_url == old.get("source_url")
        same_hash = content_hash and content_hash == old.get("dedupe", {}).get("content_hash")
        if same_url or same_hash:
            return index
    return None


def write_card(card: dict[str, Any], library_path: Path, allow_duplicates: bool, replace_existing: bool) -> str:
    library_path.parent.mkdir(parents=True, exist_ok=True)
    existing = existing_cards(library_path)
    index = duplicate_index(card, existing)
    if index is not None:
        card["dedupe"]["is_duplicate"] = True
        card["dedupe"]["duplicate_of"] = existing[index].get("material_id", "")
        if replace_existing:
            existing[index] = card
            with library_path.open("w", encoding="utf-8") as handle:
                for item in existing:
                    handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            return "replaced"
        if not allow_duplicates:
            return "duplicate"
    with library_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(card, ensure_ascii=False, sort_keys=True) + "\n")
    return "appended"


def cmd_ingest(args: argparse.Namespace) -> int:
    raw = read_json(args.input)
    profile = load_profile(args.profile)
    overrides = {
        "source_url": args.source_url,
        "platform": args.platform,
        "title": args.title,
        "author": args.author,
        "body": args.text,
        "transcript": args.transcript,
        "content_type": args.content_type,
        "_profile": profile,
    }
    card = normalize_from_raw(raw, overrides)
    card["scores"] = score_card(
        "\n\n".join(part for part in [card["title"], card["text"]["body"], card["text"]["transcript"]] if part),
        card["metrics"],
        card["tags"],
        card["signals"]["risk_flags"],
        profile,
    )
    library_path = Path(args.library).expanduser()
    action = write_card(card, library_path, args.allow_duplicates, args.replace_existing)
    result = {
        "written": action in {"appended", "replaced"},
        "action": action,
        "library": str(library_path),
        "material_id": card["material_id"],
        "duplicate": card["dedupe"]["is_duplicate"],
        "duplicate_of": card["dedupe"]["duplicate_of"],
        "score": card["scores"]["total"],
        "card": card if args.print_card else None,
    }
    print_display_json(result, args.lang)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    library_path = Path(args.library).expanduser()
    cards = existing_cards(library_path)
    if args.platform:
        cards = [card for card in cards if card.get("platform") == args.platform]
    cards.sort(key=lambda card: card.get("scores", {}).get("total", 0), reverse=True)
    summaries = []
    for card in cards[: args.limit]:
        summaries.append({
            "material_id": card.get("material_id"),
            "platform": card.get("platform"),
            "score": card.get("scores", {}).get("total"),
            "title": card.get("title"),
            "source_url": card.get("source_url"),
        })
    print_display_json(summaries, args.lang)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize extracted links into material cards.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Normalize one extraction result and append it to a JSONL library.")
    ingest.add_argument("--input", "-i", default="-", help="JSON input path, or '-' for stdin.")
    ingest.add_argument("--library", default=DEFAULT_LIBRARY, help="Material library JSONL path.")
    ingest.add_argument("--profile", help="Optional account profile JSON path.")
    ingest.add_argument("--source-url", default="", help="Override source URL.")
    ingest.add_argument("--platform", default="", help="Override platform.")
    ingest.add_argument("--title", default="", help="Override title.")
    ingest.add_argument("--author", default="", help="Override author.")
    ingest.add_argument("--text", default="", help="Override body text.")
    ingest.add_argument("--transcript", default="", help="Override transcript text.")
    ingest.add_argument("--content-type", default="", help="Override content type.")
    ingest.add_argument("--allow-duplicates", action="store_true", help="Append even if URL/hash already exists.")
    ingest.add_argument("--replace-existing", action="store_true", help="Replace an existing matching card instead of appending.")
    ingest.add_argument("--print-card", action="store_true", help="Print the full normalized card.")
    ingest.add_argument("--lang", choices=["zh", "en"], default="zh", help="Display field language. Defaults to zh.")
    ingest.set_defaults(func=cmd_ingest)

    list_cmd = subparsers.add_parser("list", help="List top material cards from a library.")
    list_cmd.add_argument("--library", default=DEFAULT_LIBRARY, help="Material library JSONL path.")
    list_cmd.add_argument("--platform", default="", help="Filter by platform.")
    list_cmd.add_argument("--limit", type=int, default=20, help="Maximum cards to print.")
    list_cmd.add_argument("--lang", choices=["zh", "en"], default="zh", help="Display field language. Defaults to zh.")
    list_cmd.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

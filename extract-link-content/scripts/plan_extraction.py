#!/usr/bin/env python3
"""Create a no-playback-first extraction plan for a platform URL."""

from __future__ import annotations

import argparse
import json
from typing import Any
from urllib.parse import urlparse


PLATFORM_HOSTS = {
    "youtube": ("youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "b23.tv"),
    "xiaohongshu": ("xiaohongshu.com", "xhslink.com"),
    "douyin": ("douyin.com", "iesdouyin.com"),
    "x": ("x.com", "twitter.com"),
    "reddit": ("reddit.com", "redd.it"),
}

ZH_KEYS = {
    "source_url": "来源链接",
    "platform": "平台",
    "goal": "目标",
    "open_page_by_default": "默认打开页面",
    "play_media_by_default": "默认播放媒体",
    "fast_path": "快路径",
    "fallback_path": "兜底路径",
    "when_playback_is_allowed": "何时允许播放",
    "notes": "注意事项",
    "step": "步骤",
    "tool": "工具",
    "purpose": "用途",
    "command": "命令",
    "condition": "触发条件",
}

ZH_VALUES = {
    "no": "否",
    "material": "素材入库",
    "full_content": "完整内容",
    "comments": "含评论",
    "unknown": "未知",
}


def classify_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for platform, suffixes in PLATFORM_HOSTS.items():
        if any(host == suffix or host.endswith("." + suffix) for suffix in suffixes):
            return platform
    return "generic"


def q(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def youtube_plan(url: str, goal: str) -> dict[str, Any]:
    return {
        "fast_path": [
            {
                "step": 1,
                "tool": "yt-dlp",
                "purpose": "不打开页面，使用已授权 Chrome cookie 读取标题、简介、频道、发布时间、缩略图和互动数据",
                "command": f"yt-dlp --cookies-from-browser chrome --ignore-no-formats --dump-json {q(url)}",
            },
            {
                "step": 2,
                "tool": "yt-dlp",
                "purpose": "不打开页面，使用已授权 Chrome cookie 重试字幕下载",
                "command": (
                    "yt-dlp --cookies-from-browser chrome --ignore-no-formats "
                    "--write-auto-sub --write-sub --sub-langs \"zh.*,en.*\" "
                    f"--skip-download -o \"/tmp/%(id)s.%(ext)s\" {q(url)}"
                ),
            },
            {
                "step": 3,
                "tool": "material_intake.py",
                "purpose": "如果没有字幕，仍可用元数据、简介、缩略图和互动数据做素材入库",
                "command": "material_intake.py ingest --input /tmp/raw.json --platform youtube --print-card",
            },
        ],
        "fallback_path": [
            {
                "condition": "yt-dlp 无法读取元数据，且用户明确允许使用可能打开或激活 Chrome 标签页的 Browser Bridge",
                "tool": "opencli",
                "purpose": "读取浏览器会话中可见的视频元数据或字幕；这不是默认路径",
                "command": f"opencli youtube video {q(url)} -f json && opencli youtube transcript {q(url)} -f md",
            },
            {
                "condition": "用户明确要求完整视频内容且没有字幕",
                "tool": "transcription backend",
                "purpose": "使用已配置的本地/授权转写后端处理音频；优先下载音频，不通过浏览器播放",
                "command": "需要先配置转写后端，本 skill 当前不内置音频转写",
            },
        ],
    }


def bilibili_plan(url: str, goal: str) -> dict[str, Any]:
    return {
        "fast_path": [
            {
                "step": 1,
                "tool": "opencli",
                "purpose": "读取视频标题、简介、作者和互动数据",
                "command": f"opencli bilibili video {q(url)} -f json",
            },
            {
                "step": 2,
                "tool": "opencli",
                "purpose": "读取字幕",
                "command": f"opencli bilibili subtitle {q(url)}",
            },
        ],
        "fallback_path": [
            {
                "condition": "OpenCLI 不接受 URL",
                "tool": "url parser",
                "purpose": "先提取 BV 号再调用 OpenCLI",
                "command": "从 URL 中提取 BV... 后运行 opencli bilibili video BV_ID -f json",
            }
        ],
    }


def opencli_post_plan(url: str, platform: str) -> dict[str, Any]:
    commands = {
        "x": [
            ("opencli twitter article TWEET_ID -f md", "读取 X Article"),
            ("opencli twitter thread TWEET_ID -f json", "读取推文线程、媒体和引用内容"),
        ],
        "xiaohongshu": [
            (f"opencli xiaohongshu note {q(url)} -f yaml", "读取笔记正文和媒体元数据"),
            ("opencli xiaohongshu comments NOTE_ID -f yaml", "仅在用户要求评论时读取评论"),
        ],
        "reddit": [
            (f"opencli reddit read {q(url)} -f yaml", "读取帖子正文、外链、媒体预览和评论元数据"),
        ],
    }
    return {
        "fast_path": [
            {"step": index + 1, "tool": "opencli", "purpose": purpose, "command": command}
            for index, (command, purpose) in enumerate(commands[platform])
        ],
        "fallback_path": [
            {
                "condition": "登录态失效、权限不足或平台要求验证",
                "tool": "user authorization",
                "purpose": "请用户在已连接 Browser Bridge 的 Chrome 中正常重新登录或验证",
                "command": "opencli doctor && opencli auth status",
            }
        ],
    }


def douyin_plan(url: str, goal: str) -> dict[str, Any]:
    return {
        "fast_path": [
            {
                "step": 1,
                "tool": "yt-dlp",
                "purpose": "不打开页面，读取可公开暴露的视频元数据",
                "command": f"yt-dlp --cookies-from-browser chrome --dump-json {q(url)}",
            },
            {
                "step": 2,
                "tool": "opencli",
                "purpose": "如果 URL 详情不可用，用标题或关键词搜索定位素材",
                "command": "opencli douyin search \"QUERY_FROM_TITLE_OR_TOPIC\" --limit 3 -f json",
            },
        ],
        "fallback_path": [
            {
                "condition": "命令行元数据不可用，但登录浏览器能看到页面文字",
                "tool": "opencli browser",
                "purpose": "读取页面文本块，不播放视频，只保留目标视频附近内容",
                "command": (
                    f"opencli browser douyin-test tab new {q(url)} && "
                    "opencli browser douyin-test get text body --tab TAB_ID"
                ),
            }
        ],
    }


def generic_plan(url: str, goal: str) -> dict[str, Any]:
    return {
        "fast_path": [
            {
                "step": 1,
                "tool": "curl",
                "purpose": "读取公开网页正文",
                "command": f"curl -s {q('https://r.jina.ai/' + url)}",
            }
        ],
        "fallback_path": [
            {
                "condition": "Reader 返回登录墙、空壳或脚本壳，且内容可在授权浏览器中正常查看",
                "tool": "opencli browser",
                "purpose": "读取页面文本，不做交互式播放",
                "command": f"opencli browser page-fetch tab new {q(url)}",
            }
        ],
    }


def build_plan(url: str, goal: str) -> dict[str, Any]:
    platform = classify_platform(url)
    if platform == "youtube":
        paths = youtube_plan(url, goal)
    elif platform == "bilibili":
        paths = bilibili_plan(url, goal)
    elif platform in {"x", "xiaohongshu", "reddit"}:
        paths = opencli_post_plan(url, platform)
    elif platform == "douyin":
        paths = douyin_plan(url, goal)
    else:
        paths = generic_plan(url, goal)

    return {
        "source_url": url,
        "platform": platform,
        "goal": goal,
        "open_page_by_default": "no",
        "play_media_by_default": "no",
        **paths,
        "when_playback_is_allowed": "仅当用户明确要求完整音视频内容、无字幕/正文可用、且已配置合法转写或人工检查流程时才考虑；默认不播放。",
        "notes": [
            "先使用命令行/API/字幕/元数据快路径。",
            "浏览器只作为登录态或页面文本兜底，不作为默认入口。",
            "素材判断可以只用标题、简介、互动数据、缩略图和可见正文，但必须标明没有完整逐字稿。",
        ],
    }


def localize(value: Any, lang: str) -> Any:
    if lang == "en":
        return value
    if isinstance(value, dict):
        return {ZH_KEYS.get(key, key): localize(item, lang) for key, item in value.items()}
    if isinstance(value, list):
        return [localize(item, lang) for item in value]
    if isinstance(value, str):
        return ZH_VALUES.get(value, value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan a no-playback-first link extraction route.")
    parser.add_argument("url", help="Platform URL to plan for.")
    parser.add_argument("--goal", choices=["material", "full_content", "comments"], default="material")
    parser.add_argument("--lang", choices=["zh", "en"], default="zh")
    args = parser.parse_args()
    print(json.dumps(localize(build_plan(args.url, args.goal), args.lang), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

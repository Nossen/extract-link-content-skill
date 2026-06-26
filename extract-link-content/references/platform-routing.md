# Platform Routing

Use this reference after classifying a user-provided link. Prefer commands that emit JSON/YAML or plain text. Store intermediate files under `/tmp/`.

## Preflight

```bash
command -v opencli yt-dlp curl
opencli doctor
```

Use installed upstream tools directly. Keep the local tool set small: OpenCLI for browser-session platforms, yt-dlp for video metadata/captions, and curl for generic public pages.

Before using a browser fallback, generate a route plan:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/plan_extraction.py" "URL"
```

Default policy:

- Do not open a browser tab just to inspect a link when metadata, captions, transcript, or post text can be read through CLI/API routes.
- Do not play video/audio by default.
- Use Browser Bridge as a fallback only for login/session-backed page text, platform-specific URL resolution, or content that the CLI exposes only through the authorized browser session.
- If a video has no captions,素材判断 can continue from title, description, visible metadata, thumbnail, and engagement. Full video content requires a configured transcription backend; browser playback is not the default path.

OpenCLI requires Browser Bridge for session-backed site adapters. If `opencli doctor` reports `Extension: not connected`, ask the user to install or enable the extension and load the unpacked extension folder that was prepared locally:

```text
$HOME/Documents/opencli-extension-v1.0.20
```

After Browser Bridge connects, ask the user to log in once per platform in that Chrome profile. There is no single cross-platform login state; platform cookies are domain-bound. Once the user has completed normal login for a platform, future extraction should reuse that saved browser session automatically.

Useful read-only checks after setup:

```bash
opencli auth status
opencli twitter whoami -f json
opencli xiaohongshu feed --limit 1 -f json
opencli douyin whoami -f json
opencli bilibili whoami -f json
opencli youtube whoami -f json
opencli reddit whoami -f json
```

## Persistent Authorized Sessions

Reuse saved sessions only through normal platform/tool mechanisms:

- `opencli`: reuse the user's logged-in browser profile and extension connection.
- Generic websites: reuse a user-approved browser profile or explicit cookie header for that site.

Stop and ask for re-authorization on expired cookies, MFA, captcha, permission denial, or suspicious account checks. Do not add evasive retry loops.

For internal/staging targets owned by the user, prefer explicit test access:

```bash
# Examples only; use the target system's documented variables or config.
export TEST_AUTH_TOKEN="..."
export TEST_SESSION_COOKIE="..."
```

Do not use these variables against third-party platforms unless they are the user's own legitimate credentials for that platform.

## YouTube

Goal: title, description, metadata, captions/transcript.

```bash
yt-dlp --cookies-from-browser chrome --ignore-no-formats --dump-json "URL"
yt-dlp --write-auto-sub --write-sub --sub-langs "zh.*,en.*" --skip-download -o "/tmp/%(id)s.%(ext)s" "URL"
yt-dlp --cookies-from-browser chrome --ignore-no-formats --write-auto-sub --write-sub --sub-langs "zh.*,en.*" --skip-download -o "/tmp/%(id)s.%(ext)s" "URL"
```

Use `yt-dlp` first for YouTube because OpenCLI's YouTube adapter may use Browser Bridge and can open, activate, or autoplay a Chrome tab. Do not run `opencli youtube video` or `opencli youtube transcript` by default. Use those only after telling the user they may touch Chrome and receiving explicit approval.

Use captions when available. If subtitle download partially succeeds but a language hits 429, use the successfully written subtitle file and report the rate-limited language. If no captions are available, report that transcript extraction needs an audio transcription backend. For素材判断, title, description, metadata, thumbnail, and engagement are acceptable if the report clearly says no full transcript was extracted.

## Bilibili / B站

Goal: video metadata, visible description, subtitle when configured.

```bash
opencli bilibili video BV_ID -f json
opencli bilibili subtitle BV_ID
```

Do not start with `yt-dlp` for Bilibili. If only a URL is available, extract the `BV...` id first.

## Xiaohongshu / 小红书

Goal: note text, image/video metadata, comments when requested.

Desktop path:

```bash
opencli xiaohongshu note "NOTE_URL" -f yaml
opencli xiaohongshu comments NOTE_ID -f yaml
```

Xiaohongshu usually requires a valid note URL and may require `xsec_token` from search/feed results. If the link cannot be read directly, use OpenCLI search or open the note through the logged-in Browser Bridge session. Stop on captcha, login failure, or permission denial.

## X / Twitter

Goal: tweet text, quoted tweet, linked article, media metadata, replies when requested.

```bash
opencli twitter article TWEET_ID -f md
opencli twitter thread TWEET_ID -f json
```

Use OpenCLI after Browser Bridge is connected. If the tweet only contains a `t.co` URL, expand it and classify the destination. X Articles often require login cookies.

## Reddit

Goal: post title/body, subreddit, score/comment metadata, comments when requested.

```bash
opencli reddit read POST_ID -f yaml
```

Reddit has no reliable anonymous path. If OpenCLI fails, ask for a logged-in Browser Bridge session or official API access.

## Douyin / 抖音

Goal: video title/description, author, music/caption text when exposed, transcript only if captions or a transcription backend exists.

Try metadata/search extraction first:

```bash
opencli douyin search "QUERY_FROM_TITLE_OR_TOPIC" --limit 3 -f json
yt-dlp --dump-json "URL"
yt-dlp --cookies-from-browser chrome --dump-json "URL"
```

OpenCLI's Douyin adapter may not expose a stable arbitrary-video-URL detail command. If `yt-dlp` reports fresh-cookie errors, use the logged-in Browser Bridge as a fallback:

```bash
opencli browser douyin-test tab new "URL"
opencli browser douyin-test get text body --tab "TAB_ID"
opencli browser douyin-test close
```

For Browser fallback output, keep only the target video block around the video title/ID, author, caption/description, chapter/summary text, stats, and comments. Do not treat the whole page/recommendation feed as source content. Do not promise a direct video file URL or full transcript unless it is explicitly exposed or a transcription backend is configured.

## Generic Web URL

Goal: readable article/body text and metadata.

```bash
TARGET_URL="https://example.com/article"
READER_HOST="https://r.jina.ai/"
curl -s "${READER_HOST}${TARGET_URL}"
```

If the result is an app shell, login wall, or empty metadata page, use browser inspection only when the content is accessible in the user's authorized browser session.

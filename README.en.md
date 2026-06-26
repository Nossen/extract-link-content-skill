# extract-link-content skill

Codex skill for extracting readable content from platform links, with a focus on YouTube, Bilibili, Xiaohongshu, X/Twitter, Reddit, Douyin, and generic web URLs.

This repository contains the skill files plus the installation notes needed to reproduce the local setup. It is intended for authorized content collection using public pages, official platform surfaces, or login sessions that the user has explicitly authorized in their own browser.

[中文说明](README.md)

## What It Does

- Classifies a user-provided link by platform.
- Reuses the user's authorized Chrome login session through OpenCLI Browser Bridge.
- Extracts source-grounded text, metadata, captions/subtitles, media URLs, image/video metadata, and comments when requested.
- Reports exact blockers such as expired login, missing captions, captcha, rate limit, deleted content, private content, or unsupported media.
- Avoids treating snippets, app shells, or recommendation-feed noise as full extracted content.

## Repository Layout

```text
extract-link-content-skill/
├── README.md
├── README.en.md
└── extract-link-content/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    ├── scripts/
    │   └── material_intake.py
    └── references/
        ├── material-workflow.md
        └── platform-routing.md
```

## Safety Boundary

Use this skill only with:

- Public content.
- Official APIs or official platform web surfaces.
- User-authorized cookies, sessions, or browser profiles.
- Internal/staging systems where the user owns the target and has provided explicit test access.

Do not use this skill to bypass login, paywalls, private-content permissions, captchas, MFA, rate limits, account checks, or anti-automation controls. If a platform asks for verification or blocks access, stop and re-authorize normally.

Never commit cookies, tokens, browser profiles, downloaded private media, or session exports to this repository.

## Install The Skill

Clone the repository:

```bash
git clone https://github.com/Nossen/extract-link-content-skill.git
cd extract-link-content-skill
```

Install the skill into Codex:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
rsync -a extract-link-content "${CODEX_HOME:-$HOME/.codex}/skills/"
```

Restart Codex or open a new Codex session so the skill list refreshes.

## Install Runtime Dependencies

The minimal local tool set is:

- `opencli`: browser-session platform adapter.
- `yt-dlp`: video metadata and subtitle fallback.
- `curl`: generic public page fallback.
- Chrome or Chromium: stores the user-authorized login sessions.

### 1. Install OpenCLI

```bash
npm install -g @jackwener/opencli@latest
opencli --version
```

OpenCLI requires Node.js 20 or newer.

### 2. Install yt-dlp

Use an isolated venv so the project does not depend on global Python packages:

```bash
mkdir -p "$HOME/.codex/tools" "$HOME/.local/bin"
python3 -m venv "$HOME/.codex/tools/link-tools-venv"
"$HOME/.codex/tools/link-tools-venv/bin/python" -m pip install --upgrade pip yt-dlp==2026.6.9
ln -sf "$HOME/.codex/tools/link-tools-venv/bin/yt-dlp" "$HOME/.local/bin/yt-dlp"
```

Make sure `~/.local/bin` is on PATH. For zsh:

```bash
grep -q 'HOME/.local/bin' "$HOME/.zshenv" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshenv"
```

Verify:

```bash
yt-dlp --version
```

### 3. Install OpenCLI Browser Bridge

Download and unpack the OpenCLI Chrome extension. This example uses the version tested with this skill:

```bash
mkdir -p "$HOME/Documents/opencli-extension-v1.0.20"
curl -L -o /tmp/opencli-extension-v1.0.20.zip \
  https://github.com/jackwener/OpenCLI/releases/download/v1.8.4/opencli-extension-v1.0.20.zip
unzip -q /tmp/opencli-extension-v1.0.20.zip -d "$HOME/Documents/opencli-extension-v1.0.20"
```

Load it in Chrome:

1. Open `chrome://extensions/`.
2. Enable `Developer Mode`.
3. Click `Load unpacked`.
4. Select this folder:

```text
~/Documents/opencli-extension-v1.0.20
```

Verify the bridge:

```bash
opencli doctor
```

Expected result:

```text
[OK] Daemon: running
[OK] Extension: connected
[OK] Connectivity: connected
```

## One-Time Platform Login Setup

Use the same Chrome profile where the OpenCLI extension is installed.

Log in normally to each platform you want to extract from:

- X/Twitter: `https://x.com`
- Xiaohongshu: `https://www.xiaohongshu.com`
- Douyin: `https://www.douyin.com`
- Bilibili: `https://www.bilibili.com`
- YouTube: `https://www.youtube.com`
- Reddit: `https://www.reddit.com`

If you also need Xiaohongshu creator-center data, log in separately to:

```text
https://creator.xiaohongshu.com
```

After login, run read-only checks:

```bash
opencli auth status
opencli twitter whoami -f json
opencli xiaohongshu feed --limit 1 -f json
opencli douyin whoami -f json
opencli bilibili whoami -f json
opencli youtube whoami -f json
opencli reddit whoami -f json
```

Platform cookies are domain-bound. There is no single universal login state, but after each platform is logged in once in the same Chrome profile, OpenCLI can reuse those sessions automatically until the platform expires or challenges the session.

## Usage Examples

Extract an X/Twitter article or thread:

```bash
opencli twitter article TWEET_ID -f md
opencli twitter thread TWEET_ID -f json
```

Extract a Xiaohongshu note:

```bash
opencli xiaohongshu note "FULL_NOTE_URL_WITH_XSEC_TOKEN" -f yaml
```

Extract Bilibili metadata and subtitles:

```bash
opencli bilibili video BV_ID -f json
opencli bilibili subtitle BV_ID -f json
```

Extract YouTube metadata and subtitles:

```bash
opencli youtube video "YOUTUBE_URL" -f json
opencli youtube transcript "YOUTUBE_URL" -f md
yt-dlp --cookies-from-browser chrome --ignore-no-formats \
  --write-auto-sub --write-sub --sub-langs "zh.*,en.*" \
  --skip-download -o "/tmp/%(id)s.%(ext)s" "YOUTUBE_URL"
```

Extract Reddit post details:

```bash
opencli reddit read "POST_URL_OR_ID" -f yaml
```

Douyin URL fallback:

```bash
opencli douyin search "QUERY_FROM_TITLE_OR_TOPIC" --limit 3 -f json
opencli browser douyin-test tab new "DOUYIN_VIDEO_URL"
opencli browser douyin-test get text body --tab "TAB_ID"
opencli browser douyin-test close
```

For Douyin browser fallback, keep only the target video block around the video title, author, caption, chapter or summary text, stats, and comments. Do not treat the full recommendation feed as clean source content.

## Material Intake, Scoring, And Deduplication

When the goal is account material collection rather than reading a single link, normalize the extraction result into a material card and store it in a local JSONL library.

Default library path:

```text
~/Documents/link-content-materials/materials.jsonl
```

After saving a raw extraction JSON result to `/tmp/raw-extraction.json`, run:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --print-card
```

Optional local account profile:

```text
~/.codex/extract-link-content/profile.json
```

Example:

```json
{
  "account_name": "my-content-account",
  "keywords": ["AI", "agent", "automation", "creator tools"],
  "avoid_keywords": ["movie", "music", "piracy"],
  "target_platforms": ["xiaohongshu", "douyin", "youtube"],
  "content_formats": ["short_video", "image_post", "thread"]
}
```

Ingest with profile-aware scoring:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --print-card
```

Command output uses Chinese field labels by default for Chinese content workflows. Add `--lang en` for English field labels:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --print-card \
  --lang en
```

List top cards:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" list \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --limit 20
```

The `list` command prints an indented JSON array with Chinese field labels by default so it is readable in the terminal and easy to pass to later analysis steps. Use `--lang en` for English field labels.

The script writes `material-card-v1` records with title, author, platform, body text, transcript, comments, media, metrics, risk flags, reuse angles, scoring, and dedupe status. Terminal output defaults to Chinese field labels; the stored library keeps the stable English schema for compatibility, dedupe, and future upgrades. Keep the library, profile, and extraction output local; do not commit them.

If the same link is already in the library but extraction or parser logic has improved, refresh the existing card:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --replace-existing \
  --print-card
```

## Validation

Validate the skill folder if your Codex installation includes the system `skill-creator` validator:

```bash
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  "$HOME/.codex/skills/extract-link-content"
```

Expected result:

```text
Skill is valid!
```

## Maintenance Notes

- Keep the repository free of cookies, tokens, profile data, downloaded media, and temporary extraction output.
- Prefer updating `extract-link-content/references/platform-routing.md` when platform command behavior changes.
- Prefer updating `extract-link-content/references/material-workflow.md` and `extract-link-content/scripts/material_intake.py` for material-intake workflows.
- Re-run the skill validator after every change.

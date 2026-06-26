---
name: extract-link-content
description: Extract readable content from user-provided platform links, especially YouTube, Bilibili/B站, Xiaohongshu/小红书, X/Twitter, Reddit, Douyin/抖音, and generic web URLs. Use when the user asks to read, crawl, fetch, extract, summarize from source, get captions/transcripts, inspect a post, capture video/article/image-post content, collect account素材, save material candidates, score/dedupe素材, or build a local material library from one or more links.
---

# Extract Link Content

Use this skill to turn a platform URL into source-grounded text that can be summarized, translated, archived, or analyzed later.

## Boundaries

- Use only public content, official APIs, configured upstream tools, or user-authorized login sessions/cookies.
- Do not bypass login, paywalls, private content restrictions, captchas, account checks, rate limits, or anti-automation systems.
- Do not describe or implement stealth, fingerprint spoofing, captcha solving, proxy rotation for evasion, token theft, session hijacking, or access-control bypass.
- When blocked, report the blocker and the legitimate unlock path: user login, Cookie-Editor export, OpenCLI browser session, official API, or manual access.

## Authorized Persistent Login

It is acceptable to reuse a user-authorized login state across future extraction requests when all of these are true:

- The user owns or is allowed to use the account/session.
- The credential was explicitly provided by the user or created by an interactive login the user completed.
- The session is stored only in the platform tool's documented config, an OS credential store, environment variables, or another user-approved location outside the workspace.
- Future fetches use the saved session normally; they do not bypass MFA, captcha, paywalls, account checks, private-content permissions, or rate limits.
- If the session expires or the platform asks for verification, stop and ask the user to re-authorize.

Preferred one-time authorization flow:

1. Ask the user which platform to authorize.
2. Use the platform's normal login path: pre-authenticated browser profile, OpenCLI Browser Bridge extension, Cookie-Editor header export, official API token, or the upstream CLI's documented login command.
3. Verify with a harmless read-only request.
4. Reuse that stored session automatically for later links from the same platform.
5. Never print raw cookies/tokens in final output.

## Internal Test Environments

For user-owned internal systems or approved staging environments, use explicit test access instead of bypassing login:

- Use provided test credentials, OAuth tokens, API keys, session cookies, or a pre-authenticated browser profile.
- Use documented test-only auth switches only when the user confirms the target system is owned by them and the switch already exists in that environment.
- Use mocks, fixtures, exported HTML/JSON, or recorded API responses when the goal is parser/extraction validation rather than live access.
- Keep credentials out of the workspace; use environment variables, the platform's configured credential store, `/tmp/` for ephemeral files, or the tool's documented config path.
- Stop on unexpected authentication failure, captcha, permission denial, or production-domain mismatch.

## Success Criteria

- Identify the platform and content type before choosing tools.
- Extract the strongest available source content: post text, article body, title, description, captions/transcript, visible media metadata, image text when available, and comments only when requested.
- Preserve source boundaries: report what was fetched, what was inferred, and what was blocked by login, permissions, captions, deletion, region, rate limit, or anti-automation.
- Do not claim full extraction when only metadata, embed text, OCR, or search snippets were available.

## Workflow

1. Normalize the URL and classify the platform.
2. Plan the route before opening a browser: `python scripts/plan_extraction.py "URL"`.
3. Check installed upstream tools and any stored authorized session for that platform.
4. Choose the platform command from [platform-routing.md](references/platform-routing.md), starting with no-page fast paths.
5. Store temporary downloads, captions, screenshots, and parsed output in `/tmp/`, not in the user's workspace.
6. If the user's goal is素材收集、选题库、账号内容参考、批量找素材、入库、评分, or去重, read [material-workflow.md](references/material-workflow.md) and use `scripts/material_intake.py`.
   - User-facing material JSON should use Chinese field labels by default. Use `--lang en` only when the user asks for English output or machine-oriented English fields.
7. Return a compact extraction report with:
   - `source_url`
   - `platform`
   - `tool_used`
   - `content_available`
   - `extracted_text`
   - `media_metadata`
   - `comments_or_replies` when requested
   - `blockers`
   - `next_legitimate_unlock_step`
   - `confidence`
   - `material_card` when ingested into a material library

## Routing Rules

- Use the smallest configured tool set first: `opencli` for supported browser-session platforms, `yt-dlp` for video metadata/captions, and `curl` with Jina Reader for generic public pages.
- Do not open a browser tab or play media by default. Browser use is a fallback for login/session verification or page-only text after command-line/API routes fail.
- For YouTube, do not run OpenCLI YouTube commands by default because they can drive Chrome through Browser Bridge. Prefer `yt-dlp --cookies-from-browser chrome --ignore-no-formats --dump-json` plus subtitle download commands, which do not open or play a page.
- For other video platforms, prefer official captions, automatic captions, descriptions, and metadata before downloading media. Only transcribe audio when a local or configured transcription tool is available and the user explicitly needs full audio/video content.
- For Xiaohongshu, X/Twitter, Reddit, and Douyin, expect login, cookie, anti-automation, or region blockers. Use the user's existing authenticated session or configured cookies; stop if access is denied.
- For Bilibili, do not use `yt-dlp` as the first path. Prefer `opencli bilibili video` and `opencli bilibili subtitle` when Browser Bridge is configured.
- For generic pages, use Jina Reader first. If it returns a login wall or script shell, switch to browser/OpenCLI only when the content is accessible in the user's authorized browser session.
- For account material collection, normalize extraction results with `scripts/material_intake.py` so later runs can search, score, and dedupe a local素材库.

## Failure Handling

If extraction fails, report the exact blocker and the next legitimate unlock step. Examples:

- Tool missing: install or configure the upstream platform tool.
- Cookie missing: ask the user to configure the platform cookie or use OpenCLI with a logged-in browser.
- Captions missing: report that no captions were exposed and offer transcription if a transcription backend is available.
- Private/deleted/region-locked content: stop and state that the source is not reachable from this environment.

Never continue with stale snippets as if they were full source content.

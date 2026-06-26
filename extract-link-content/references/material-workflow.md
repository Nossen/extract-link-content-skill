# Material Workflow

Use this reference after extracting source content when the user's goal is素材收集、选题库、账号内容参考、爆款拆解、批量找素材、入库、去重、评分, or later reuse.

## Output Goal

Create a stable `material-card-v1` record for each source item:

- source URL, platform, content type
- title, author, publish/capture time
- body text, transcript, comments when requested
- media metadata and media URLs when exposed
- tags, metrics, risk flags
- reuse angles, pain points, hook candidate
- deterministic score and duplicate status

## Local Library

Default library path:

```text
~/Documents/link-content-materials/materials.jsonl
```

Keep this library outside the skill repository. Do not commit material libraries, cookies, tokens, or downloaded media.

## Account Profile

Optional profile path:

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

The profile is local configuration. Do not store personal account details in the public skill repository.

## Ingest Workflow

1. Extract the source with the platform route in `platform-routing.md`.
2. Save the raw extraction JSON under `/tmp/`.
3. Run:

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --print-card
```

4. Report the normalized card summary with Chinese field labels by default:
   - 素材ID
   - 是否重复
   - 总分和评分明细
   - 标题钩子
   - 复用角度
   - 风险标记
   - 素材库路径

Use `--lang en` only when English field labels are needed. The stored JSONL library keeps the stable `material-card-v1` English schema for compatibility.

## Batch Workflow

For multiple links, repeat extraction and ingestion per link. Do not download large media by default. Store only metadata, exposed media URLs, subtitles, and text unless the user explicitly asks to download files.

## Scoring

The script scores these dimensions:

- `topic_value`: tags, engagement, and relevance signals
- `hook_strength`: title/opening strength, numbers, questions, strong terms
- `adaptability`: whether it can be turned into a tutorial, comparison, explainer, or case study
- `discussion_potential`: comments, controversy, contrast, or question-driven discussion
- `account_fit`: optional profile keyword match
- `risk`: copyright/repost/media risk indicators
- `total`: weighted total score from 0 to 100

Use the score as a triage aid, not as proof of content quality.

## Deduplication

The script detects duplicates by:

- exact `source_url`
- normalized content hash

If duplicate and `--allow-duplicates` is not set, it reports the existing material ID and does not append another record. Use `--replace-existing` when a parser or extraction upgrade should refresh the existing matching card instead of appending a duplicate.

## Comments

When the user asks for comments, include top comments in the raw extraction before ingesting. Summarize high-signal comments in the final response, but do not claim the script has semantically summarized comments; it stores comment text and metadata only.

## Failure Handling

If ingestion fails:

- invalid JSON: inspect the raw extraction output and convert it to valid JSON
- missing URL: pass `--source-url`
- wrong platform: pass `--platform`
- duplicate: report the existing material ID
- profile missing: continue without profile or create the profile locally

# extract-link-content skill

用于 Codex 的链接内容抓取 skill，面向 YouTube、B站、小红书、X/Twitter、Reddit、抖音和通用网页链接。

这个仓库包含 skill 文件和可复现的安装说明。它的目标是通过公开页面、官方平台页面、官方接口，或用户明确授权过的浏览器登录态，抓取可读内容、视频字幕、媒体信息和评论等素材。

[English README](README.en.md)

## 功能

- 根据链接识别平台和内容类型。
- 通过 OpenCLI Browser Bridge 复用用户已授权的 Chrome 登录态。
- 抓取正文、标题、描述、作者、发布时间、互动数据、字幕、媒体 URL、图片/视频信息。
- 按需抓取评论或回复。
- 明确报告失败原因，例如登录过期、验证码、无字幕、429 限流、内容删除、私密内容、地区限制或工具缺失。
- 避免把搜索片段、空壳页面、App shell、推荐流噪音当成完整正文。

## 仓库结构

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

## 安全边界

只能用于以下场景：

- 公开内容。
- 官方 API 或官方平台网页。
- 用户自己授权的 Cookie、登录态或浏览器 profile。
- 用户拥有的内部测试环境，并且用户提供了明确的测试访问方式。

不要用这个 skill 绕过登录、付费墙、私密内容权限、验证码、MFA、限流、账号检查或平台反自动化机制。平台要求验证或拒绝访问时，应停止并按正常方式重新授权。

不要把 Cookie、token、浏览器 profile、下载的私密媒体、登录态导出文件提交到本仓库。

## 安装 Skill

克隆仓库：

```bash
git clone https://github.com/Nossen/extract-link-content-skill.git
cd extract-link-content-skill
```

安装到 Codex 的 skills 目录：

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
rsync -a extract-link-content "${CODEX_HOME:-$HOME/.codex}/skills/"
```

重启 Codex，或打开一个新的 Codex 会话，让 skill 列表刷新。

## 安装运行依赖

最小依赖是：

- `opencli`：复用浏览器登录态的平台适配器。
- `yt-dlp`：视频元数据和字幕兜底工具。
- `curl`：通用公开网页兜底工具。
- Chrome 或 Chromium：保存用户授权过的平台登录态。

### 1. 安装 OpenCLI

```bash
npm install -g @jackwener/opencli@latest
opencli --version
```

OpenCLI 需要 Node.js 20 或更高版本。

### 2. 安装 yt-dlp

建议放到独立 venv，避免污染项目环境：

```bash
mkdir -p "$HOME/.codex/tools" "$HOME/.local/bin"
python3 -m venv "$HOME/.codex/tools/link-tools-venv"
"$HOME/.codex/tools/link-tools-venv/bin/python" -m pip install --upgrade pip yt-dlp==2026.6.9
ln -sf "$HOME/.codex/tools/link-tools-venv/bin/yt-dlp" "$HOME/.local/bin/yt-dlp"
```

确认 `~/.local/bin` 在 PATH 里。zsh 可以这样设置：

```bash
grep -q 'HOME/.local/bin' "$HOME/.zshenv" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshenv"
```

验证：

```bash
yt-dlp --version
```

### 3. 安装 OpenCLI Browser Bridge

下载并解压 OpenCLI Chrome 扩展。下面是本 skill 测试过的版本：

```bash
mkdir -p "$HOME/Documents/opencli-extension-v1.0.20"
curl -L -o /tmp/opencli-extension-v1.0.20.zip \
  https://github.com/jackwener/OpenCLI/releases/download/v1.8.4/opencli-extension-v1.0.20.zip
unzip -q /tmp/opencli-extension-v1.0.20.zip -d "$HOME/Documents/opencli-extension-v1.0.20"
```

在 Chrome 里加载扩展：

1. 打开 `chrome://extensions/`。
2. 打开右上角 `Developer Mode`。
3. 点击 `Load unpacked`。
4. 选择这个文件夹：

```text
~/Documents/opencli-extension-v1.0.20
```

验证 Browser Bridge：

```bash
opencli doctor
```

期望看到：

```text
[OK] Daemon: running
[OK] Extension: connected
[OK] Connectivity: connected
```

## 一次性登录配置

使用安装了 OpenCLI 扩展的同一个 Chrome profile。

在这个 Chrome 里正常登录你要抓取的平台：

- X/Twitter：`https://x.com`
- 小红书：`https://www.xiaohongshu.com`
- 抖音：`https://www.douyin.com`
- B站：`https://www.bilibili.com`
- YouTube：`https://www.youtube.com`
- Reddit：`https://www.reddit.com`

如果后续还需要读取小红书创作者后台数据，再单独登录：

```text
https://creator.xiaohongshu.com
```

登录完成后，运行只读检查：

```bash
opencli auth status
opencli twitter whoami -f json
opencli xiaohongshu feed --limit 1 -f json
opencli douyin whoami -f json
opencli bilibili whoami -f json
opencli youtube whoami -f json
opencli reddit whoami -f json
```

各平台 Cookie 是按域名隔离的，不存在一个登录态通吃所有平台。正确做法是在同一个 Chrome profile 中分别登录一次各平台。之后 OpenCLI 会自动复用这些登录态，直到平台让你重新登录或重新验证。

## 使用示例

### X/Twitter

抓取 X Article 或线程：

```bash
opencli twitter article TWEET_ID -f md
opencli twitter thread TWEET_ID -f json
```

### 小红书

抓取笔记正文和互动数据：

```bash
opencli xiaohongshu note "FULL_NOTE_URL_WITH_XSEC_TOKEN" -f yaml
```

小红书笔记通常需要完整 URL 和 `xsec_token`。如果直接链接不可读，可以先用搜索或首页 feed 获取完整链接。

### B站

抓取视频元数据和字幕：

```bash
opencli bilibili video BV_ID -f json
opencli bilibili subtitle BV_ID -f json
```

### YouTube

抓取元数据和字幕：

```bash
opencli youtube video "YOUTUBE_URL" -f json
opencli youtube transcript "YOUTUBE_URL" -f md
yt-dlp --cookies-from-browser chrome --ignore-no-formats \
  --write-auto-sub --write-sub --sub-langs "zh.*,en.*" \
  --skip-download -o "/tmp/%(id)s.%(ext)s" "YOUTUBE_URL"
```

YouTube 字幕有时需要 Chrome cookies。某些语言字幕请求可能触发 429，此时使用已成功下载的字幕，并报告被限流的语言。

### Reddit

抓取帖子正文、图片/视频预览、外链和评论：

```bash
opencli reddit read "POST_URL_OR_ID" -f yaml
```

### 抖音

优先用搜索拿到视频链接和基础信息：

```bash
opencli douyin search "QUERY_FROM_TITLE_OR_TOPIC" --limit 3 -f json
```

如果需要按视频 URL 抽取页面内容，可用 Browser Bridge 兜底：

```bash
opencli browser douyin-test tab new "DOUYIN_VIDEO_URL"
opencli browser douyin-test get text body --tab "TAB_ID"
opencli browser douyin-test close
```

抖音 Browser 兜底输出可能包含推荐流、侧栏和页面配置。处理结果时只保留目标视频块附近的标题、作者、描述、章节/摘要、互动数据和评论，不要把整页内容当成干净正文。

## 素材入库、评分和去重

当目标不是只读一个链接，而是给账号找素材时，可以把抓取结果标准化成素材卡片并写入本地素材库。

默认素材库路径：

```text
~/Documents/link-content-materials/materials.jsonl
```

把一次抓取的 JSON 结果保存到 `/tmp/raw-extraction.json` 后运行：

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --print-card
```

可选账号定位配置：

```text
~/.codex/extract-link-content/profile.json
```

示例：

```json
{
  "account_name": "my-content-account",
  "keywords": ["AI", "agent", "automation", "creator tools"],
  "avoid_keywords": ["movie", "music", "piracy"],
  "target_platforms": ["xiaohongshu", "douyin", "youtube"],
  "content_formats": ["short_video", "image_post", "thread"]
}
```

带账号定位评分：

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --print-card
```

命令行输出默认使用中文字段，适合中文内容选题和复盘。如果需要英文版字段，增加 `--lang en`：

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --print-card \
  --lang en
```

查看高分素材：

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" list \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --limit 20
```

`list` 命令会输出缩进格式化的中文字段 JSON 数组，方便直接阅读或复制给后续分析步骤。英文版同样使用 `--lang en`。

脚本会生成 `material-card-v1`，包含标题、作者、平台、正文、字幕、评论、媒体信息、互动数据、风险标记、复用角度、评分和去重状态。终端展示默认是中文字段；素材库内部仍保留稳定的英文 schema，方便程序兼容、去重和后续升级。素材库、账号配置和抓取结果都应保存在本地，不要提交到公开仓库。

如果同一个链接已经入库，但你升级了抓取或解析逻辑，可以刷新已有记录：

```bash
python "$HOME/.codex/skills/extract-link-content/scripts/material_intake.py" ingest \
  --input "/tmp/raw-extraction.json" \
  --library "$HOME/Documents/link-content-materials/materials.jsonl" \
  --profile "$HOME/.codex/extract-link-content/profile.json" \
  --replace-existing \
  --print-card
```

## 验证 Skill

如果你的 Codex 环境包含系统 `skill-creator` 校验脚本，可以运行：

```bash
python "$HOME/.codex/skills/.system/skill-creator/scripts/quick_validate.py" \
  "$HOME/.codex/skills/extract-link-content"
```

期望结果：

```text
Skill is valid!
```

## 维护建议

- 不要提交 Cookie、token、浏览器 profile、媒体下载文件或临时抓取输出。
- 平台命令发生变化时，优先更新 `extract-link-content/references/platform-routing.md`。
- 素材采集流程优先更新 `extract-link-content/references/material-workflow.md` 和 `extract-link-content/scripts/material_intake.py`。
- 每次修改后重新运行 skill 校验。

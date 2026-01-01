---
name: downloader-core
description: 批量资源下载 Skill - 自动识别URL类型，选择最优工具，支持验证
allowed-tools: Bash(*), Read(*), Write(*), Glob(*), Grep(*)
model_preference: haiku
---

# Downloader Core Skill

## Purpose

Downloader 是**批量资源下载**模块。自动识别 URL 类型，选择最优下载工具，支持并行下载和结果验证。

**核心能力**：
- URL 类型识别 (VIDEO/GALLERY/DIRECT/TORRENT/WEBSITE)
- 工具自动选择 (aria2c/yt-dlp/gallery-dl/wget2/curl)
- 并行批量下载
- 下载结果验证 (文件存在 + 大小 + hash)
- Envelope-First 输出

## Sources of Truth

> **本文件是 Downloader 的唯一事实源。**

| 文件 | 角色 |
|------|------|
| `.claude/skills/downloader-core/SKILL.md` | **唯一事实源** |
| `.claude/skills/downloader-core/patterns.yaml` | **URL 分类规则** |
| `.claude/skills/downloader-core/tools.yaml` | **工具配置** |
| `.claude/commands/downloader.md` | Thin wrapper（用户可直接 /downloader） |

---

## Trigger

Downloader 被触发的条件：

1. **用户显式调用**：`/downloader <URL>` 或 `/downloader -f urls.txt`
2. **参数**：`$ARGUMENTS` 为 URL 或 URL 列表

### 自动触发条件 (PROACTIVELY 使用)

当满足以下任一条件时，**必须**自动调用 downloader skill：

1. **用户消息包含可下载的 URL**：
   - 检测到 HTTP/HTTPS URL 且匹配已知下载模式（见 patterns.yaml）
   - 用户明确提到"下载"、"获取"、"保存"等关键词 + URL

2. **工作流需要下载资源**：
   - 用户要求"下载视频"、"保存图片"、"获取文件"等任务
   - 对话中出现 GitHub release URL、网盘分享链接、资源托管链接

3. **批量资源处理需求**：
   - 用户提供 URL 列表文件（urls.txt）
   - 对话中出现多个相关下载链接（≥3个）

4. **特定命令上下文**：
   - 在 `analyzetools/` 目录下讨论工具下载时
   - 在 `analyzedata/inputs/` 目录下讨论资源获取时

### 自动触发行为

```yaml
WHEN: <满足上述任一条件>
THEN:
  - 提取所有匹配的 URL
  - 自动调用 Skill(skill: "downloader-core", args: "<URLs>")
  - LOG: "[downloader] 检测到下载需求，自动触发"
  - 输出 Envelope 格式结果
```

### 禁止绕过规则

以下场景**禁止**绕过 downloader skill，必须调用：

- 用户提供的 URL 超过 100MB（大文件下载）
- 视频/音频 URL（YouTube, Bilibili 等）
- 画廊/相册 URL（Pixiv, Twitter media 等）
- 网盘/文件托管 URL（Mega, MediaFire, 蓝奏云等）
- Torrent/磁力链接

---

## Inputs

| 输入 | 必需 | 说明 |
|------|------|------|
| `$ARGUMENTS` | Yes | URL / URL列表 / 文件路径 |
| `-o, --output` | No | 输出目录 (默认: ./downloads) |
| `-f, --file` | No | 从文件读取 URL 列表 |
| `--parallel` | No | 并行数 (默认: 4) |
| `--tool` | No | 强制使用指定工具 |
| `--verify` | No | 下载后验证 hash |
| `--mirror` | No | 网站镜像模式 |

---

## Tool Chain (优先级)

### 工具优先级（锁死顺序）

| 优先级 | 工具 | 用途 | 安装检查 |
|--------|------|------|----------|
| **0** | **jdownloader** | 网盘/文件托管 (500+ sites, via MyJDownloader API) | `python -c "import myjdapi"` |
| 1 | **aria2c** | 通用高速下载 (HTTP/FTP/BT/磁力) | `aria2c --version` |
| 2 | **yt-dlp** | 视频/音频 (1000+ 站点) | `yt-dlp --version` |
| 3 | **gallery-dl** | 图片画廊 (Pixiv/Twitter/120+ 站点) | `gallery-dl --version` |
| 4 | **wget2** | 通用下载/网站镜像 | `wget2 --version` |
| 5 | **curl** | 单文件/兜底 | `curl --version` |

### Tool Probe (必需步骤)

```yaml
tool_probe:
  timestamp: <ISO8601>
  available:
    aria2c: <true|false>
    yt-dlp: <true|false>
    gallery-dl: <true|false>
    wget2: <true|false>
    curl: <true|false>
  versions:
    aria2c: "1.37.0"
    yt-dlp: "2024.12.13"
    # ...
```

---

## URL Classification

### 分类规则（按优先级匹配）

| 类型 | 匹配模式 | 推荐工具 | 备选工具 |
|------|----------|----------|----------|
| **FILEHOST** | mega.nz, mediafire.com, 百度网盘, 115, 蓝奏云 etc. | jdownloader | aria2c |
| **VIDEO** | youtube.com, bilibili.com, vimeo.com, twitch.tv, etc. | yt-dlp | - |
| **GALLERY** | pixiv.net, twitter.com/*/media, deviantart.com, artstation.com | gallery-dl | - |
| **TORRENT** | *.torrent, magnet:? | aria2c | - |
| **DIRECT** | *.zip, *.rar, *.7z, *.exe, *.iso, *.dmg, *.tar.gz | aria2c | wget2, curl |
| **WEBSITE** | --mirror 标志 或 递归需求 | wget2 | httrack |
| **GENERIC** | 其他 HTTP/HTTPS | aria2c | wget2, curl |

### 详细匹配规则

见 [patterns.yaml](patterns.yaml)

---

## Command Templates

### aria2c (通用高速)
```bash
# 单文件
aria2c -x 16 -s 16 -k 1M -d <output_dir> "<URL>"

# 批量 (从文件)
aria2c -x 16 -s 16 -k 1M -d <output_dir> -i urls.txt

# BT/磁力
aria2c --seed-time=0 -d <output_dir> "<magnet:?...>"
```

### yt-dlp (视频)
```bash
# 最佳质量
yt-dlp -f "bestvideo+bestaudio/best" -o "<output_dir>/%(title)s.%(ext)s" "<URL>"

# 配合 aria2c 加速
yt-dlp --downloader aria2c --downloader-args "-x 16 -s 16" "<URL>"

# 仅音频
yt-dlp -x --audio-format mp3 -o "<output_dir>/%(title)s.%(ext)s" "<URL>"
```

### gallery-dl (图片画廊)
```bash
# 基本下载
gallery-dl -d <output_dir> "<URL>"

# Pixiv (需要认证)
gallery-dl -d <output_dir> --cookies-from-browser chrome "<URL>"

# Twitter
gallery-dl -d <output_dir> "<URL>"
```

### wget2 (通用/镜像)
```bash
# 单文件
wget2 -P <output_dir> "<URL>"

# 网站镜像
wget2 -r -l 2 --max-threads=8 -P <output_dir> "<URL>"
```

### curl (兜底)
```bash
curl -L -o <output_path> "<URL>"
```

---

## Authentication (Session 30)

### 需要认证的站点

| 类型 | 站点 | 认证方式 |
|------|------|----------|
| VIDEO | youtube.com | cookies-from-browser (推荐) |
| VIDEO | vimeo.com | cookies-from-browser |
| VIDEO | bilibili.com | cookies-from-browser |
| GALLERY | pixiv.net | **OAuth** 或 cookies-from-browser |
| GALLERY | fanbox.cc | Pixiv OAuth |
| GALLERY | twitter.com | cookies-from-browser |

### 解决方案 (voteplan 251230221500-e8a2 winner)

**方案: cookies-from-browser (推荐)**

```bash
# yt-dlp - 使用 Chrome 登录状态
yt-dlp --cookies-from-browser chrome "https://www.youtube.com/watch?v=xxx"

# gallery-dl - 使用 Chrome 登录状态
gallery-dl --cookies-from-browser chrome "https://www.pixiv.net/users/xxx"
```

支持的浏览器: `chrome`, `firefox`, `edge`, `brave`, `opera`, `safari`

### 一次性配置

#### yt-dlp 持久化配置
```powershell
# Windows
mkdir -p $env:APPDATA/yt-dlp
echo "--cookies-from-browser chrome" > $env:APPDATA/yt-dlp/config
```

#### gallery-dl OAuth (Pixiv)
```bash
# 执行后会打开浏览器进行授权
gallery-dl oauth:pixiv
```

#### 安装 deno (yt-dlp 2024+ 需要)
```powershell
winget install DenoLand.Deno
# 验证
deno --version
```

### JDownloader 2 Setup (网盘下载)

#### 1. 安装 JDownloader 2
```powershell
# 下载 JDownloader.jar
mkdir D:\tools\jdownloader2
curl -L -o D:\tools\jdownloader2\JDownloader.jar http://installer.jdownloader.org/JDownloader.jar

# 首次运行 (GUI 模式，配置 MyJDownloader 账号)
java -jar D:\tools\jdownloader2\JDownloader.jar
```

#### 2. 配置 MyJDownloader
1. 访问 [my.jdownloader.org](https://my.jdownloader.org) 注册账号
2. 在 JD2 GUI 中: Settings → MyJDownloader → 登录
3. 等待设备出现在 MyJDownloader 网页端

#### 3. 安装 Python 库
```powershell
pip install myjdapi
```

#### 4. 配置环境变量
```powershell
# 添加到系统环境变量或 .env 文件
setx MYJD_EMAIL "your@email.com"
setx MYJD_PASSWORD "your_password"
# 可选: 指定设备名
setx MYJD_DEVICE "your_device_name"
```

#### 5. Headless 运行 (后台)
```powershell
# 配置完成后，可以无界面运行
javaw -jar D:\tools\jdownloader2\JDownloader.jar -norestart
```

#### 6. 验证
```powershell
python -c "import myjdapi; print('myjdapi OK')"
```

### 认证故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| "Sign in to confirm you're not a bot" | YouTube 机器人检测 | 使用 `--cookies-from-browser chrome` |
| "Invalid or missing login credentials" | Pixiv OAuth 失效 | 重新运行 `gallery-dl oauth:pixiv` |
| 格式列表缺失 | 缺少 JS 运行时 | 安装 deno |
| 403 Forbidden | IP 不匹配 | 确保 cookies 来源 IP 与下载 IP 一致 |

---

## Workflow

```
1. 解析输入
   ↓ URL 为空 → ERROR (INSUFFICIENT_INPUT)

2. Tool Probe
   ↓ 所有工具不可用 → ERROR (NO_TOOLS_AVAILABLE)

3. URL 分类 (按 patterns.yaml)
   ↓ 生成任务队列

4. 选择工具
   ↓ 按类型优先级 + 可用性

5. 执行下载 (并行)
   ↓ 监控进度

6. 验证结果
   ↓ 文件存在 + 大小 > 0
   ↓ 可选: hash 校验

7. 输出 Envelope + 清单
```

---

## Verification

### 下载验证规则

| 检查项 | 方法 | 失败处理 |
|--------|------|----------|
| 文件存在 | `Test-Path $path` | 标记 FAILED |
| 文件大小 | `(Get-Item $path).Length -gt 0` | 标记 FAILED |
| Hash (可选) | `Get-FileHash -Algorithm SHA256` | 标记 HASH_MISMATCH |

### 验证脚本

```powershell
function Verify-Download {
    param([string]$Path, [string]$ExpectedHash)

    if (-not (Test-Path $Path)) {
        return @{ Status = "FAILED"; Error = "File not found" }
    }

    $size = (Get-Item $Path).Length
    if ($size -eq 0) {
        return @{ Status = "FAILED"; Error = "Empty file" }
    }

    if ($ExpectedHash) {
        $actual = (Get-FileHash -Path $Path -Algorithm SHA256).Hash
        if ($actual -ne $ExpectedHash) {
            return @{ Status = "HASH_MISMATCH"; Expected = $ExpectedHash; Actual = $actual }
        }
    }

    return @{ Status = "OK"; Size = $size }
}
```

---

## Envelope Output

```yaml
envelope:
  command: downloader
  timestamp: <ISO8601>
  status: OK|PARTIAL|ERROR
  error_code: <null|TOOL_MISSING|DOWNLOAD_FAILED|ALL_FAILED>
  warnings: []
  artifacts_written:
    - <output_dir>/file1.zip
    - <output_dir>/file2.mp4

tool_probe:
  aria2c: true
  yt-dlp: true
  gallery-dl: false
  wget2: true
  curl: true

download_summary:
  total_urls: 5
  successful: 4
  failed: 1
  total_size_bytes: 1234567890

results:
  - url: "https://example.com/file.zip"
    type: DIRECT
    tool: aria2c
    status: OK
    output_path: "./downloads/file.zip"
    size_bytes: 12345678
    sha256: "abc123..."
    duration_seconds: 15

  - url: "https://youtube.com/watch?v=xxx"
    type: VIDEO
    tool: yt-dlp
    status: OK
    output_path: "./downloads/Video Title.mp4"
    size_bytes: 987654321

  - url: "https://example.com/missing.zip"
    type: DIRECT
    tool: aria2c
    status: FAILED
    error: "HTTP 404 Not Found"
```

---

## Error Codes

| 错误码 | 级别 | 含义 | 触发条件 |
|--------|------|------|----------|
| `INSUFFICIENT_INPUT` | ERROR | 输入不足 | 无 URL |
| `NO_TOOLS_AVAILABLE` | ERROR | 无可用工具 | 所有工具都未安装 |
| `TOOL_MISSING` | WARNING | 工具缺失 | 推荐工具未安装，使用备选 |
| `DOWNLOAD_FAILED` | WARNING | 单个下载失败 | HTTP 错误/网络问题 |
| `ALL_FAILED` | ERROR | 全部失败 | 所有 URL 下载失败 |
| `HASH_MISMATCH` | WARNING | Hash 不匹配 | 文件损坏或被篡改 |
| `TIMEOUT` | WARNING | 下载超时 | 超过设定超时时间 |

### Status 判定

- `OK`: 所有 URL 下载成功
- `PARTIAL`: 部分成功部分失败
- `ERROR`: 全部失败或致命错误

---

## Usage Examples

### 基本下载
```
/downloader https://example.com/file.zip
```

### 视频下载
```
/downloader https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### 批量下载
```
/downloader https://url1.com/a.zip https://url2.com/b.zip
```

### 从文件读取
```
/downloader -f urls.txt -o ./output
```

### 强制使用工具
```
/downloader --tool wget2 https://example.com/file.zip
```

### 网站镜像
```
/downloader --mirror https://docs.example.com/
```

---

## Final Summary Template

```
---
ENVELOPE: <status> | <error_code if any>
TOOLS: aria2c(<Y/N>), yt-dlp(<Y/N>), gallery-dl(<Y/N>), wget2(<Y/N>), curl(<Y/N>)
URLS: <total> | SUCCESS: <N> | FAILED: <N>
SIZE: <total size formatted>
OUTPUT: <output_dir>
---
```

---

## Files

```
.claude/skills/downloader-core/
├── SKILL.md              # 本文件（唯一事实源）
├── patterns.yaml         # URL 分类规则
├── tools.yaml            # 工具配置
├── CHECKLIST.md          # 验收清单
└── verify_downloader.ps1 # 验证脚本
```

---

*创建时间: 2025-12-30*
*优先级: MEDIUM*

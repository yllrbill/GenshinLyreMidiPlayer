# /downloader - 批量资源下载

> **唯一事实源**: `.claude/skills/downloader-core/SKILL.md`

## 用途

批量下载资源，自动识别 URL 类型并选择最优工具。

## 使用方法

```
/downloader <URL>                    # 单个 URL
/downloader <URL1> <URL2> ...        # 多个 URL
/downloader -f urls.txt              # 从文件读取
/downloader -o ./output <URL>        # 指定输出目录
/downloader --tool aria2c <URL>      # 强制使用工具
/downloader --mirror <URL>           # 网站镜像模式
```

## 参数

| 参数 | 说明 |
|------|------|
| `-o, --output` | 输出目录 (默认: ./downloads) |
| `-f, --file` | 从文件读取 URL 列表 |
| `--parallel` | 并行数 (默认: 4) |
| `--tool` | 强制使用指定工具 |
| `--verify` | 下载后验证 hash |
| `--mirror` | 网站镜像模式 |

## 支持的 URL 类型

| 类型 | 示例站点 | 工具 |
|------|----------|------|
| VIDEO | YouTube, Bilibili, Twitch | yt-dlp |
| GALLERY | Pixiv, Twitter, DeviantArt | gallery-dl |
| TORRENT | magnet:?, *.torrent | aria2c |
| DIRECT | *.zip, *.exe, *.iso | aria2c |
| WEBSITE | 任意 (--mirror) | wget2 |

## 示例

### 下载 YouTube 视频
```
/downloader https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### 下载 Pixiv 画廊
```
/downloader https://www.pixiv.net/users/12345/artworks
```

### 批量下载文件
```
/downloader https://example.com/file1.zip https://example.com/file2.zip
```

### 网站镜像
```
/downloader --mirror https://docs.example.com/
```

## 工具优先级

1. aria2c (通用高速)
2. yt-dlp (视频)
3. gallery-dl (图片画廊)
4. wget2 (通用/镜像)
5. curl (兜底)

## 执行流程

调用 `downloader-core` Skill:

1. 解析输入 URL
2. 检测可用工具
3. URL 分类
4. 选择最优工具
5. 执行下载
6. 验证结果
7. 输出 Envelope

## 输出

```yaml
envelope:
  command: downloader
  status: OK|PARTIAL|ERROR

download_summary:
  total_urls: 5
  successful: 4
  failed: 1

results:
  - url: <URL>
    tool: aria2c
    status: OK
    output_path: ./downloads/file.zip
```

---

*关联 Skill*: `.claude/skills/downloader-core/SKILL.md`

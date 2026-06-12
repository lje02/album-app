# ══════════════════════════════════════════════════════════════════
#  [新增] URL 扫描 & 媒体批量下载功能  v2.0
#  将此代码块追加到主脚本 bot.py 的 if __name__ == "__main__": 之前
#  无需修改任何原有代码。
# ══════════════════════════════════════════════════════════════════
#
# 依赖安装（首次使用前执行）：
#   pip install aiohttp beautifulsoup4
#
# .env 可选配置项（均有默认值，不配置也能直接使用）：
#   URL_MIN_FILE_SIZE=102400     # 图片过滤阈值，默认 100 KB
#   URL_MIN_VIDEO_SIZE=524288    # 视频过滤阈值，默认 512 KB
#   URL_MIN_AUDIO_SIZE=51200     # 音频过滤阈值，默认 50 KB
#   URL_DL_CONCURRENCY=4         # 图片并发下载数
#   URL_DL_CONCURRENCY_V=2       # 视频并发下载数（大文件建议保守）
#   URL_DL_CONCURRENCY_A=3       # 音频并发下载数
#   URL_DL_TIMEOUT_VIDEO=600     # 视频单文件超时(s)，大文件可调大
#   URL_MAX_IMAGES=200           # 单次最多处理文件数
#   URL_PROGRESS_EVERY=3         # 每 N 个更新一次进度消息
# ──────────────────────────────────────────────────────────────────

from url_scanner import scan_and_download, MIN_FILE_SIZE, MIN_VIDEO_SIZE, MIN_AUDIO_SIZE
from url_scanner import fmt_size as sc_fmt   # 避免与主脚本同名函数冲突

import re as _re


# ── URL 检测正则 ──────────────────────────────────────────────────
_URL_RE = _re.compile(
    r'https?://(?:[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+)',
    _re.IGNORECASE,
)

def _extract_url(text: str) -> str | None:
    m = _URL_RE.search(text or "")
    return m.group(0) if m else None


# ── /url 命令 ────────────────────────────────────────────────────
@bot.on_message(filters.command("url") & (filters.private | filters.group))
async def cmd_url(_, msg: Message):
    if not is_allowed(_uid(msg)): return

    parts = msg.text.split(maxsplit=1)
    raw   = parts[1].strip() if len(parts) > 1 else ""
    url   = _extract_url(raw)

    if not url:
        await msg.reply_text(
            "🌐 **URL 媒体批量下载**\n\n"
            "**用法：**\n"
            "`/url https://example.com/gallery`\n\n"
            "**支持媒体类型：**\n"
            "  🖼️ 图片  `jpg png webp gif avif` 等\n"
            "  🎬 视频  `mp4 mkv webm mov` 等\n"
            "  🎵 音频  `mp3 flac aac ogg m4a` 等\n\n"
            "**过滤规则：**\n"
            f"  图片 ≥ {sc_fmt(MIN_FILE_SIZE)}  "
            f"视频 ≥ {sc_fmt(MIN_VIDEO_SIZE)}  "
            f"音频 ≥ {sc_fmt(MIN_AUDIO_SIZE)}\n\n"
            "**支持页面类型：**\n"
            "• 普通网页（自动提取 img / video / audio 标签）\n"
            "• 媒体直链列表页（danbooru / pixiv gallery 等）\n"
            "• 媒体文件直链（单个文件直接下载）\n\n"
            "也可以直接把链接发给我，自动识别 🎯"
        )
        return

    await _do_url_download(msg, url)


# ── 自动识别纯文本 URL ───────────────────────────────────────────
@bot.on_message(filters.text & (filters.private | filters.group))
async def handle_text_url(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    if msg.text and msg.text.startswith("/"): return
    url = _extract_url(msg.text)
    if not url: return
    await _do_url_download(msg, url)


# ── 核心执行 ─────────────────────────────────────────────────────
async def _do_url_download(msg: Message, url: str):
    uid       = _uid(msg)
    status    = await msg.reply_text(f"🌐 正在分析链接...\n`{url[:80]}`")
    last_text = [""]

    async def update_status(text: str):
        if text == last_text[0]: return
        last_text[0] = text
        try:
            await status.edit_text(text)
        except Exception:
            pass

    # 注册回调
    async def reg(path: Path, mtype: str, u: int | None):
        await async_db_register(path, mtype, u)

    # 各媒体类型的保存根目录（直接用主脚本的 MEDIA_DIRS）
    media_roots = {
        "photo": MEDIA_DIRS.get("photo", DOWNLOAD_ROOT / "photos"),
        "video": MEDIA_DIRS.get("video", DOWNLOAD_ROOT / "videos"),
        "audio": MEDIA_DIRS.get("audio", DOWNLOAD_ROOT / "audios"),
    }

    try:
        result = await scan_and_download(
            url         = url,
            save_root   = media_roots["photo"],
            min_size    = MIN_FILE_SIZE,
            status_cb   = update_status,
            register_cb = reg,
            uid         = uid,
            media_roots = media_roots,
        )
    except Exception as exc:
        logger.error(f"URL 下载失败 [{url}]: {exc}")
        await status.edit_text(
            f"❌ **下载失败**\n\n`{exc}`",
            reply_markup=kb_back("menu:home"),
        )
        return

    by_type = result.get("by_type", {})
    folder  = result["folder"]
    total   = result["total_found"]
    skipped = result["skipped"]
    dl      = result["downloaded"]
    fail    = result["failed"]

    # ── 结果消息 ──────────────────────────────────────────────────
    lines = [f"✅ **URL 批量下载完成！**\n"]
    lines.append(f"🌐 `{url[:60]}`")
    lines.append(f"📁 目录：`{folder}`\n")
    lines.append(f"🔍 发现媒体：**{total}** 个  过滤：**{skipped}** 个\n")

    for mtype, emoji in [("photo","🖼️"), ("video","🎬"), ("audio","🎵")]:
        info = by_type.get(mtype, {})
        d, f_ = info.get("downloaded", 0), info.get("failed", 0)
        if d or f_:
            lines.append(f"  {emoji} {mtype}：✅ {d} 个" + (f"  ❌ {f_} 失败" if f_ else ""))

    lines.append(f"\n⬇️ 合计下载：**{dl}** 个" + (f"  ❌ 失败 **{fail}** 个" if fail else ""))

    # 动态按钮：根据实际下载了哪些类型生成浏览快捷键
    type_buttons = []
    browse_map = {"photo": ("🖼️ 浏览图片", "browse:photo:0"),
                  "video": ("🎬 浏览视频", "browse:video:0"),
                  "audio": ("🎵 浏览音频", "browse:audio:0")}
    for mtype, (label, cb) in browse_map.items():
        if by_type.get(mtype, {}).get("downloaded", 0) > 0:
            type_buttons.append(InlineKeyboardButton(label, callback_data=cb))

    kb_rows = []
    if type_buttons:
        # 每行最多 2 个按钮
        kb_rows += [type_buttons[i:i+2] for i in range(0, len(type_buttons), 2)]
    kb_rows.append([
        InlineKeyboardButton("📊 查看统计", callback_data="menu:status"),
        InlineKeyboardButton("🏠 主菜单",   callback_data="menu:home"),
    ])

    await status.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(kb_rows),
    )
    logger.info(
        f"🌐 URL下载 [{url}] 完成: "
        f"图片{by_type.get('photo',{}).get('downloaded',0)} "
        f"视频{by_type.get('video',{}).get('downloaded',0)} "
        f"音频{by_type.get('audio',{}).get('downloaded',0)} "
        f"过滤{skipped} 失败{fail} 目录={folder}"
    )

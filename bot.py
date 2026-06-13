#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 自动下载机器人 · Pyrogram 版  v3.0 (性能极致优化重构版)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ MTProto 协议 — 无文件大小限制
✅ 实时进度条（速度 / 剩余时间）
✅ 8 种媒体类型自动分类保存
✅ 内联按钮管理菜单
✅ 按日期子目录归档
✅ 用户白名单
✅ 【⚡重构】安全并发下载控制（防止资源溢出）
✅ 【⚡重构】全异步非阻塞架构（不卡顿不失联）
✅ 【⚡重构】DB 驱动级菜单渲染（万级文件毫秒响应）
✅ SQLite 持久化注册表 / 文件回传 / 模糊搜索
"""

import asyncio
import logging
import os
import sqlite3
import time
import re as _re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from url_router import smart_download

# ══════════════════════════════════════════════
#  加载 .env
# ══════════════════════════════════════════════
load_dotenv()

def _require(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v or v.lower().startswith("your_"):
        raise RuntimeError(f"❌ 请在 .env 中填写 {key}")
    return v

def _int_require(key: str) -> int:
    v = _require(key)
    try:
        return int(v)
    except ValueError:
        raise RuntimeError(f"❌ {key} 必须是整数，当前值：{v!r}")

API_ID    = _int_require("API_ID")
API_HASH  = _require("API_HASH")
BOT_TOKEN = _require("BOT_TOKEN")

DOWNLOAD_ROOT       = Path(os.getenv("DOWNLOAD_ROOT", "./downloads"))
ORGANIZE_BY_DATE    = os.getenv("ORGANIZE_BY_DATE", "true").lower() == "true"
PROGRESS_UPDATE_SEC = float(os.getenv("PROGRESS_UPDATE_SEC", "2.0"))
PAGE_SIZE           = int(os.getenv("PAGE_SIZE", "8"))
DB_PATH             = Path(os.getenv("DB_PATH", "./tg_downloader.db"))
ALLOWED_USERS: list[int] = [
    int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip().isdigit()
]

# 【NEW】最大并发下载数控制
CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", "3"))
_DOWNLOAD_SEMAPHORE: asyncio.Semaphore = None

def get_semaphore() -> asyncio.Semaphore:
    """懒加载信号量，完美规避 Python 3.10+ 在 Loop 启动前实例化引发的崩溃"""
    global _DOWNLOAD_SEMAPHORE
    if _DOWNLOAD_SEMAPHORE is None:
        _DOWNLOAD_SEMAPHORE = asyncio.Semaphore(CONCURRENT_DOWNLOADS)
    return _DOWNLOAD_SEMAPHORE

# ══════════════════════════════════════════════
#  媒体目录映射
# ══════════════════════════════════════════════
MEDIA_DIRS: dict[str, Path] = {
    "photo"     : DOWNLOAD_ROOT / "photos",
    "video"     : DOWNLOAD_ROOT / "videos",
    "audio"     : DOWNLOAD_ROOT / "audios",
    "voice"     : DOWNLOAD_ROOT / "voices",
    "document"  : DOWNLOAD_ROOT / "documents",
    "sticker"   : DOWNLOAD_ROOT / "stickers",
    "animation" : DOWNLOAD_ROOT / "animations",
    "video_note": DOWNLOAD_ROOT / "video_notes",
}

ENABLED_TYPES: dict[str, bool] = {k: True for k in MEDIA_DIRS}

# ══════════════════════════════════════════════
#  SQLite 持久化层
# ══════════════════════════════════════════════
_FILE_REGISTRY: dict[int, Path] = {}   # fid → Path
_PATH_TO_FID:   dict[str, int]  = {}   # resolved_str → fid

@contextmanager
def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def db_init():
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                path          TEXT    UNIQUE NOT NULL,
                media_type    TEXT    NOT NULL,
                file_name     TEXT    NOT NULL,
                file_size     INTEGER NOT NULL DEFAULT 0,
                downloaded_at TEXT    NOT NULL,
                downloaded_by INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON files(media_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_file_name  ON files(file_name)")

def db_load_registry():
    with _db() as conn:
        rows = conn.execute("SELECT id, path FROM files").fetchall()
    stale = []
    for row in rows:
        fid, raw = row["id"], row["path"]
        p = Path(raw)
        if p.exists():
            _FILE_REGISTRY[fid] = p
            _PATH_TO_FID[str(p.resolve())] = fid
        else:
            stale.append(fid)
    if stale:
        with _db() as conn:
            conn.executemany("DELETE FROM files WHERE id=?", [(i,) for i in stale])

def db_register(path: Path, media_type: str, uid: int | None) -> int:
    key = str(path.resolve())
    if key in _PATH_TO_FID:
        return _PATH_TO_FID[key]
    stat = path.stat()
    with _db() as conn:
        conn.execute(
            """INSERT INTO files(path,media_type,file_name,file_size,downloaded_at,downloaded_by)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 file_size=excluded.file_size,
                 downloaded_at=excluded.downloaded_at""",
            (key, media_type, path.name, stat.st_size,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid),
        )
        fid = conn.execute("SELECT id FROM files WHERE path=?", (key,)).fetchone()["id"]
    _FILE_REGISTRY[fid] = path
    _PATH_TO_FID[key]   = fid
    return fid

def db_unregister(fid: int):
    p = _FILE_REGISTRY.pop(fid, None)
    if p:
        _PATH_TO_FID.pop(str(p.resolve()), None)
    with _db() as conn:
        conn.execute("DELETE FROM files WHERE id=?", (fid,))

def db_search(keyword: str, limit: int = 50) -> list:
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM files WHERE file_name LIKE ? ORDER BY downloaded_at DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()

def db_get_row(fid: int):
    with _db() as conn:
        return conn.execute("SELECT * FROM files WHERE id=?", (fid,)).fetchone()

# 异步化业务层包装，防止主循环在执行数据库或本地磁盘读写时挂起
async def async_db_register(path: Path, media_type: str, uid: int | None) -> int:
    return await asyncio.to_thread(db_register, path, media_type, uid)

async def async_db_search(keyword: str, limit: int = 50) -> list:
    return await asyncio.to_thread(db_search, keyword, limit)

async def async_db_get_row(fid: int):
    return await asyncio.to_thread(db_get_row, fid)

def _lookup_path(fid: int) -> Path | None:
    return _FILE_REGISTRY.get(fid)

# ══════════════════════════════════════════════
#  日志
# ══════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  Pyrogram 客户端
# ══════════════════════════════════════════════
bot = Client(
    "tg_downloader_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="session",
)

# ══════════════════════════════════════════════
#  工具函数
# ══════════════════════════════════════════════
def fmt_size(n: int) -> str:
    if n < 1024:     return f"{n} B"
    if n < 1 << 20:  return f"{n/1024:.1f} KB"
    if n < 1 << 30:  return f"{n/(1<<20):.1f} MB"
    return f"{n/(1<<30):.2f} GB"

def fmt_speed(bps: float) -> str:
    if bps < 1024:    return f"{bps:.0f} B/s"
    if bps < 1 << 20: return f"{bps/1024:.1f} KB/s"
    return f"{bps/(1<<20):.1f} MB/s"

def fmt_eta(sec: float) -> str:
    sec = max(0, int(sec))
    h, r = divmod(sec, 3600); m, s = divmod(r, 60)
    if h: return f"{h}h {m:02d}m"
    if m: return f"{m}m {s:02d}s"
    return f"{s}s"

def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def pbar(pct: float, width: int = 16) -> str:
    f = int(width * pct / 100)
    return "█" * f + "░" * (width - f)

def media_emoji(t: str) -> str:
    return {"photo":"🖼️","video":"🎬","audio":"🎵","voice":"🎤",
            "document":"📄","sticker":"😄","animation":"🎞️","video_note":"📹"}.get(t,"📁")

def get_save_dir(media_type: str) -> Path:
    base = MEDIA_DIRS.get(media_type, DOWNLOAD_ROOT / "others")
    if ORGANIZE_BY_DATE:
        base = base / datetime.now().strftime("%Y-%m-%d")
    base.mkdir(parents=True, exist_ok=True)
    return base

def safe_path(save_dir: Path, name: str) -> Path:
    p = save_dir / name
    if p.exists():
        stem, suffix = Path(name).stem, Path(name).suffix
        p = save_dir / f"{stem}_{datetime.now().strftime('%H%M%S%f')}{suffix}"
    return p

def is_allowed(uid: int | None) -> bool:
    if uid is None: return True
    return not ALLOWED_USERS or uid in ALLOWED_USERS

def detect_media(msg: Message) -> tuple[str, str] | tuple[None, None]:
    mid = msg.id
    if msg.photo:      return "photo",     f"photo_{mid}.jpg"
    if msg.video:      return "video",      msg.video.file_name     or f"video_{mid}.mp4"
    if msg.audio:      return "audio",      msg.audio.file_name     or f"audio_{mid}.mp3"
    if msg.voice:      return "voice",      f"voice_{mid}.ogg"
    if msg.document:   return "document",   msg.document.file_name  or f"document_{mid}"
    if msg.sticker:
        s = msg.sticker
        ext = ".webm" if s.is_video else (".tgs" if s.is_animated else ".webp")
        return "sticker", f"sticker_{mid}{ext}"
    if msg.animation:  return "animation",  msg.animation.file_name or f"animation_{mid}.mp4"
    if msg.video_note: return "video_note", f"videonote_{mid}.mp4"
    return None, None

def get_file_size(msg: Message) -> int:
    for attr in ("photo","video","audio","voice","document","sticker","animation","video_note"):
        obj = getattr(msg, attr, None)
        if obj:
            return getattr(obj, "file_size", 0) or 0
    return 0

# ══════════════════════════════════════════════
#  【⚡优化】高速非阻塞数据汇总
# ══════════════════════════════════════════════
def _list_files_sync(mtype: str) -> list[tuple[int, Path, int, str]]:
    """完全基于本地 DB 缓存序列读取，彻底替代极其耗时的硬盘 rglob 遍历"""
    with _db() as conn:
        rows = conn.execute(
            "SELECT id, path, file_size, downloaded_at FROM files WHERE media_type=? ORDER BY downloaded_at DESC", 
            (mtype,)
        ).fetchall()
    return [(r["id"], Path(r["path"]), r["file_size"], r["downloaded_at"]) for row in rows]

async def list_files_for_type(mtype: str) -> list[tuple[int, Path, int, str]]:
    return await asyncio.to_thread(_list_files_sync, mtype)

def _calc_stats_sync() -> tuple[dict, int, int]:
    """高性能毫秒级聚合统计，不触碰任何物理磁盘 I/O"""
    per = {}; tf = ts = 0
    with _db() as conn:
        for mtype in MEDIA_DIRS:
            row = conn.execute(
                "SELECT COUNT(*), TOTAL(file_size) FROM files WHERE media_type=?", (mtype,)
            ).fetchone()
            cnt, size = row[0], int(row[1])
            per[mtype] = (cnt, size)
            tf += cnt; ts += size
    return per, tf, ts

async def calc_stats() -> tuple[dict, int, int]:
    return await asyncio.to_thread(_calc_stats_sync)

# ══════════════════════════════════════════════
#  键盘构建（全面支持异步 text 数据源接入）
# ══════════════════════════════════════════════
def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 下载统计", callback_data="menu:status"),
         InlineKeyboardButton("📁 目录结构", callback_data="menu:dirs")],
        [InlineKeyboardButton("🔍 浏览文件", callback_data="menu:browse"),
         InlineKeyboardButton("🗑️ 删除文件", callback_data="menu:delete")],
        [InlineKeyboardButton("🔧 类型开关", callback_data="menu:types"),
         InlineKeyboardButton("⚙️ 当前设置", callback_data="menu:settings")],
        [InlineKeyboardButton("🔄 刷新菜单", callback_data="menu:home")],
    ])

def kb_back(target: str = "menu:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("« 返回", callback_data=target)]])

def kb_types() -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(MEDIA_DIRS), 2):
        row = []
        for mtype in list(MEDIA_DIRS)[i:i+2]:
            flag = "✅" if ENABLED_TYPES[mtype] else "❌"
            row.append(InlineKeyboardButton(f"{flag} {media_emoji(mtype)} {mtype}",
                                            callback_data=f"toggle:{mtype}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("« 返回主菜单", callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)

async def kb_type_select(prefix: str, back: str = "menu:home") -> InlineKeyboardMarkup:
    per, _, _ = await calc_stats()
    rows = []
    for i in range(0, len(MEDIA_DIRS), 2):
        row = []
        for mtype in list(MEDIA_DIRS)[i:i+2]:
            cnt = per.get(mtype, (0,))[0]
            row.append(InlineKeyboardButton(
                f"{media_emoji(mtype)} {mtype} ({cnt})",
                callback_data=f"{prefix}:{mtype}:0"))
        rows.append(row)
    rows.append([InlineKeyboardButton("« 返回主菜单", callback_data=back)])
    return InlineKeyboardMarkup(rows)

def kb_file_list(mtype: str, page: int, files: list[tuple[int, Path, int, str]]) -> InlineKeyboardMarkup:
    total_p = max(1, (len(files) + PAGE_SIZE - 1) // PAGE_SIZE)
    rows = []
    for fid, f, _, _ in files[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        rows.append([InlineKeyboardButton(f"📄 {f.name[:38]}", callback_data=f"finfo:{fid}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ 上一页", callback_data=f"browse:{mtype}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_p}", callback_data="noop"))
    if page < total_p - 1:
        nav.append(InlineKeyboardButton("下一页 ▶", callback_data=f"browse:{mtype}:{page+1}"))
    rows.append(nav)
    rows.append([
        InlineKeyboardButton("« 返回类型列表", callback_data="menu:browse"),
        InlineKeyboardButton("🏠 主菜单",      callback_data="menu:home"),
    ])
    return InlineKeyboardMarkup(rows)

def kb_file_info(fid: int, mtype: str, page: int,
                 back_search: str | None = None) -> InlineKeyboardMarkup:
    back_cb = f"search_back:{back_search}" if back_search else f"browse:{mtype}:{page}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 回传文件", callback_data=f"fsend:{fid}"),
         InlineKeyboardButton("🗑️ 删除文件", callback_data=f"fdel_ask:{fid}:{mtype}:{page}")],
        [InlineKeyboardButton("« 返回列表",  callback_data=back_cb),
         InlineKeyboardButton("🏠 主菜单",   callback_data="menu:home")],
    ])

def kb_file_del_confirm(fid: int, mtype: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⚠️ 确认删除", callback_data=f"fdel_do:{fid}:{mtype}:{page}"),
        InlineKeyboardButton("✗ 取消",      callback_data=f"finfo:{fid}"),
    ]])

async def kb_batch_type_select() -> InlineKeyboardMarkup:
    per, _, _ = await calc_stats()
    rows = []
    for i in range(0, len(MEDIA_DIRS), 2):
        row = []
        for mtype in list(MEDIA_DIRS)[i:i+2]:
            cnt = per.get(mtype, (0,))[0]
            row.append(InlineKeyboardButton(
                f"{media_emoji(mtype)} {mtype} ({cnt})",
                callback_data=f"bdel_ask:{mtype}"))
        rows.append(row)
    rows.append([
        InlineKeyboardButton("💣 删除全部",  callback_data="bdel_ask:ALL"),
        InlineKeyboardButton("« 返回主菜单", callback_data="menu:home"),
    ])
    return InlineKeyboardMarkup(rows)

def kb_batch_del_confirm(mtype: str) -> InlineKeyboardMarkup:
    label = "全部" if mtype == "ALL" else mtype
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(f"⚠️ 确认删除 {label}", callback_data=f"bdel_do:{mtype}"),
        InlineKeyboardButton("✗ 取消",               callback_data="menu:delete"),
    ]])

def kb_search_results(rows: list, keyword: str, page: int) -> InlineKeyboardMarkup:
    total_p = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    result = []
    for row in rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        fid = row["id"]
        p   = Path(row["path"])
        # 【⚡优化】直接从 row 中获取原先插入的已解析完路径，防止每次高频触发同步磁盘解析
        if fid not in _FILE_REGISTRY:
            _FILE_REGISTRY[fid] = p
            _PATH_TO_FID[row["path"]] = fid
        label = f"{media_emoji(row['media_type'])} {row['file_name'][:36]}"
        result.append([InlineKeyboardButton(
            label, callback_data=f"finfo_s:{fid}:{keyword[:20]}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀", callback_data=f"search:{keyword}:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{total_p}", callback_data="noop"))
    if page < total_p - 1:
        nav.append(InlineKeyboardButton("▶", callback_data=f"search:{keyword}:{page+1}"))
    result.append(nav)
    result.append([InlineKeyboardButton("🏠 主菜单", callback_data="menu:home")])
    return InlineKeyboardMarkup(result)

# ══════════════════════════════════════════════
#  文本构建（全面重构为 Async，确保不阻塞主频）
# ══════════════════════════════════════════════
async def text_home(name: str) -> str:
    enabled = sum(1 for v in ENABLED_TYPES.values() if v)
    _, tf, ts = await calc_stats()
    return (
        f"👋 你好，**{name}**！\n\n"
        f"📥 **Telegram 自动下载机器人**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️ 已保存文件：**{tf}** 个  ({fmt_size(ts)})\n"
        f"🔛 启用类型：**{enabled}** / {len(MEDIA_DIRS)}\n"
        f"📂 根目录：`{DOWNLOAD_ROOT.resolve()}`\n\n"
        f"直接发送或转发媒体给我，自动保存 👇\n"
        f"🔍 搜索文件：`/search 关键词`"
    )

async def text_status() -> str:
    per, tf, ts = await calc_stats()
    lines = ["📊 **下载统计**\n"]
    for mtype, (cnt, size) in per.items():
        flag = "✅" if ENABLED_TYPES[mtype] else "⏸"
        bar  = "▓" * min(cnt // max(1, tf // 10 + 1), 8) if tf else ""
        lines.append(f"  {flag} {media_emoji(mtype)} **{mtype}**：{cnt} 个  {fmt_size(size)}  {bar}")
    lines.append(f"\n📦 **合计**：{tf} 个文件，{fmt_size(ts)}")
    lines.append(f"🕐 更新时间：{datetime.now().strftime('%H:%M:%S')}")
    return "\n".join(lines)

def _text_dirs_sync() -> str:
    lines = [f"📁 **目录结构**\n`{DOWNLOAD_ROOT.resolve()}`\n"]
    with _db() as conn:
        for mtype, path in MEDIA_DIRS.items():
            exists = path.exists()
            row = conn.execute("SELECT COUNT(*) FROM files WHERE media_type=?", (mtype,)).fetchone()
            cnt = row[0] if exists else 0
            lines.append(
                f"  {'✅' if exists else '⬜'}{'▶' if ENABLED_TYPES[mtype] else '⏸'} "
                f"{media_emoji(mtype)} `{path.relative_to(DOWNLOAD_ROOT)}`  _{cnt} 个_"
            )
    return "\n".join(lines)

async def text_dirs() -> str:
    return await asyncio.to_thread(_text_dirs_sync)

def text_types() -> str:
    lines = ["🔧 **媒体类型开关**\n点击按钮切换启用 / 停用\n"]
    for mtype, enabled in ENABLED_TYPES.items():
        lines.append(f"  {media_emoji(mtype)} {mtype}：{'✅ 启用' if enabled else '❌ 停用'}")
    return "\n".join(lines)

def text_settings() -> str:
    wl = "全部用户" if not ALLOWED_USERS else "、".join(str(u) for u in ALLOWED_USERS)
    enabled_list = [k for k, v in ENABLED_TYPES.items() if v]
    return (
        "⚙️ **当前运行设置**\n\n"
        f"📂 下载根目录\n`{DOWNLOAD_ROOT.resolve()}`\n\n"
        f"💾 数据库路径\n`{DB_PATH.resolve()}`\n\n"
        f"📅 按日期归档：{'✅ 开启' if ORGANIZE_BY_DATE else '❌ 关闭'}\n"
        f"⏱ 进度刷新间隔：{PROGRESS_UPDATE_SEC}s\n"
        f"📋 每页条数：{PAGE_SIZE}\n"
        f"👤 白名单：{wl}\n\n"
        f"🔛 启用类型：{'  '.join(media_emoji(t) for t in enabled_list)}"
    )

async def text_browse_select() -> str:
    per, tf, ts = await calc_stats()
    lines = [f"🔍 **浏览文件** 共 {tf} 个 / {fmt_size(ts)}\n\n选择媒体类型："]
    for mtype, (cnt, size) in per.items():
        lines.append(f"  {media_emoji(mtype)} **{mtype}**：{cnt} 个  {fmt_size(size)}")
    return "\n".join(lines)

def text_file_list(mtype: str, page: int, files: list[tuple[int, Path, int, str]]) -> str:
    total   = len(files)
    total_p = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start   = page * PAGE_SIZE
    lines   = [f"{media_emoji(mtype)} **{mtype}** 文件列表",
               f"共 {total} 个  第 {page+1}/{total_p} 页\n"]
    for i, (_, f, file_size, downloaded_at) in enumerate(files[start:start + PAGE_SIZE], start=start + 1):
        lines.append(
            f"  `{i}.` {f.name[:36]}  "
            f"_{fmt_size(file_size)}_  "
            f"{downloaded_at[:10]}"
        )
    lines.append("\n点击文件名查看详情")
    return "\n".join(lines)

async def text_file_info(fid: int) -> str:
    p = _lookup_path(fid)
    if not p:
        return "❌ 文件不存在或已被删除"
        
    def _get_io_info():
        if not p.exists(): return None
        return p.stat(), db_get_row(fid)
        
    res = await asyncio.to_thread(_get_io_info)
    if not res:
        return "❌ 文件不存在或已被删除"
    stat, row = res
    
    rel  = p.relative_to(DOWNLOAD_ROOT) if DOWNLOAD_ROOT in p.parents else p
    dl_by = f"用户 {row['downloaded_by']}" if row and row["downloaded_by"] else "未知"
    dl_at = row["downloaded_at"] if row else "未知"
    return (
        f"📄 **文件详情**\n\n"
        f"🏷 名称：`{p.name}`\n"
        f"📦 大小：{fmt_size(stat.st_size)}\n"
        f"🕐 下载时间：{dl_at}\n"
        f"👤 下载者：{dl_by}\n"
        f"🕑 最后修改：{fmt_ts(stat.st_mtime)}\n"
        f"📂 相对路径：`{rel}`\n"
        f"💾 完整路径：\n`{p.resolve()}`"
    )

async def text_delete_select() -> str:
    per, tf, ts = await calc_stats()
    lines = [f"🗑️ **删除文件** 共 {tf} 个 / {fmt_size(ts)}\n\n选择删除范围："]
    for mtype, (cnt, size) in per.items():
        lines.append(f"  {media_emoji(mtype)} **{mtype}**：{cnt} 个  {fmt_size(size)}")
    lines.append("\n⚠️ 删除操作**不可恢复**！")
    return "\n".join(lines)

def text_search_results(keyword: str, rows: list, page: int) -> str:
    total   = len(rows)
    total_p = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start   = page * PAGE_SIZE
    if not total:
        return f"🔍 搜索 **`{keyword}`**\n\n📭 没有找到匹配的文件"
    lines = [f"🔍 搜索 **`{keyword}`** 共 {total} 条  第 {page+1}/{total_p} 页\n"]
    for i, row in enumerate(rows[start:start + PAGE_SIZE], start=start + 1):
        p      = Path(row["path"])
        lines.append(
            f"  `{i}.` {row['file_name'][:34]}  "
            f"_{fmt_size(row['file_size'])}_  "
            f"{row['downloaded_at'][:10]}"
        )
    lines.append("\n点击文件名查看详情")
    return "\n".join(lines)

# ══════════════════════════════════════════════
#  进度回调工厂
# ══════════════════════════════════════════════
def make_progress(status_msg: Message, file_name: str,
                  media_type: str, total_hint: int = 0):
    last_t  = [0.0]
    start_t = [time.monotonic()]

    async def _cb(current: int, total: int):
        now = time.monotonic()
        if (now - last_t[0]) < PROGRESS_UPDATE_SEC and current < total:
            return
        last_t[0]  = now
        total_real = total or total_hint or current
        pct        = current / total_real * 100 if total_real else 0
        elapsed    = max(now - start_t[0], 0.001)
        speed      = current / elapsed
        eta        = (total_real - current) / speed if speed > 0 and total_real > current else 0
        try:
            await status_msg.edit_text(
                f"{media_emoji(media_type)} **正在下载 (并发受控)**\n`{file_name}`\n\n"
                f"`{pbar(pct)}` **{pct:.1f}%**\n"
                f"📦 {fmt_size(current)} / {fmt_size(total_real)}\n"
                f"⚡ {fmt_speed(speed)}   ⏱ 剩余 {fmt_eta(eta)}"
            )
        except Exception:
            pass
    return _cb

def make_upload_progress(status_msg: Message, file_name: str, total_size: int):
    last_t  = [0.0]
    start_t = [time.monotonic()]

    async def _cb(current: int, total: int):
        now = time.monotonic()
        if (now - last_t[0]) < PROGRESS_UPDATE_SEC and current < total:
            return
        last_t[0]  = now
        total_real = total or total_size or current
        pct        = current / total_real * 100 if total_real else 0
        elapsed    = max(now - start_t[0], 0.001)
        speed      = current / elapsed
        try:
            await status_msg.edit_text(
                f"📤 **正在回传**\n`{file_name}`\n\n"
                f"`{pbar(pct)}` **{pct:.1f}%**\n"
                f"📦 {fmt_size(current)} / {fmt_size(total_real)}\n"
                f"⚡ {fmt_speed(speed)}"
            )
        except Exception:
            pass
    return _cb

# ══════════════════════════════════════════════
#  命令处理器
# ══════════════════════════════════════════════
def _uid(msg: Message) -> int | None:
    return msg.from_user.id if msg.from_user else None

@bot.on_message(filters.command("start") & (filters.private | filters.group))
async def cmd_start(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    name = msg.from_user.first_name if msg.from_user else "用户"
    await msg.reply_text(await text_home(name), reply_markup=kb_main())

@bot.on_message(filters.command("menu") & (filters.private | filters.group))
async def cmd_menu(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    name = msg.from_user.first_name if msg.from_user else "用户"
    await msg.reply_text(await text_home(name), reply_markup=kb_main())

@bot.on_message(filters.command("status") & (filters.private | filters.group))
async def cmd_status(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(await text_status(), reply_markup=kb_back())

@bot.on_message(filters.command("dirs") & (filters.private | filters.group))
async def cmd_dirs(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(await text_dirs(), reply_markup=kb_back())

@bot.on_message(filters.command("browse") & (filters.private | filters.group))
async def cmd_browse(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(await text_browse_select(),
                         reply_markup=await kb_type_select("browse", back="menu:home"))

@bot.on_message(filters.command("delete") & (filters.private | filters.group))
async def cmd_delete(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(await text_delete_select(), reply_markup=await kb_batch_type_select())

@bot.on_message(filters.command("search") & (filters.private | filters.group))
async def cmd_search(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.reply_text(
            "🔍 **文件搜索**\n\n用法：`/search 关键词`\n\n"
            "支持文件名模糊匹配，例如：\n"
            "`/search video`\n`/search 2024`\n`/search .mp4`"
        )
        return
    keyword = parts[1].strip()
    rows    = await async_db_search(keyword)
    await msg.reply_text(
        text_search_results(keyword, rows, 0),
        reply_markup=kb_search_results(rows, keyword, 0),
    )

# ══════════════════════════════════════════════
#  内联按钮回调
# ══════════════════════════════════════════════
def _delete_single_file_sync(fid: int):
    p = _lookup_path(fid)
    if not p or not p.exists(): return None
    name_del = p.name
    size_del = p.stat().st_size
    p.unlink()
    db_unregister(fid)
    try: p.parent.rmdir()
    except OSError: pass
    return name_del, size_del

def _batch_delete_sync(mtype: str):
    targets = (list(MEDIA_DIRS.values()) if mtype == "ALL"
               else ([MEDIA_DIRS[mtype]] if mtype in MEDIA_DIRS else []))
    deleted_cnt = deleted_size = 0
    for base in targets:
        if not base.exists(): continue
        for f in [f for f in base.rglob("*") if f.is_file()]:
            sz      = f.stat().st_size
            fid_key = _PATH_TO_FID.get(str(f.resolve()))
            f.unlink()
            deleted_cnt += 1; deleted_size += sz
            if fid_key:
                _FILE_REGISTRY.pop(fid_key, None)
                _PATH_TO_FID.pop(str(f.resolve()), None)
                with _db() as conn:
                    conn.execute("DELETE FROM files WHERE id=?", (fid_key,))
        for d in sorted(base.rglob("*"), reverse=True):
            if d.is_dir():
                try: d.rmdir()
                except OSError: pass
    return deleted_cnt, deleted_size

@bot.on_callback_query()
async def on_callback(_, cq: CallbackQuery):
    uid = cq.from_user.id
    if not is_allowed(uid):
        await cq.answer("⛔ 无权限", show_alert=True); return

    data = cq.data
    name = cq.from_user.first_name or "用户"

    if data == "noop":
        await cq.answer(); return

    elif data == "menu:home":
        await cq.message.edit_text(await text_home(name), reply_markup=kb_main())
        await cq.answer()

    elif data == "menu:status":
        await cq.message.edit_text(await text_status(), reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 刷新", callback_data="menu:status"),
            InlineKeyboardButton("« 返回",  callback_data="menu:home"),
        ]]))
        await cq.answer("已刷新")

    elif data == "menu:dirs":
        await cq.message.edit_text(await text_dirs(), reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 刷新", callback_data="menu:dirs"),
            InlineKeyboardButton("« 返回",  callback_data="menu:home"),
        ]]))
        await cq.answer()

    elif data == "menu:types":
        await cq.message.edit_text(text_types(), reply_markup=kb_types())
        await cq.answer()

    elif data.startswith("toggle:"):
        mtype = data.split(":", 1)[1]
        if mtype in ENABLED_TYPES:
            ENABLED_TYPES[mtype] = not ENABLED_TYPES[mtype]
            state = "✅ 启用" if ENABLED_TYPES[mtype] else "❌ 停用"
            await cq.answer(f"{media_emoji(mtype)} {mtype} {state}")
        await cq.message.edit_text(text_types(), reply_markup=kb_types())

    elif data == "menu:settings":
        await cq.message.edit_text(text_settings(), reply_markup=kb_back())
        await cq.answer()

    elif data == "menu:browse":
        await cq.message.edit_text(await text_browse_select(),
                                   reply_markup=await kb_type_select("browse", back="menu:home"))
        await cq.answer()

    elif data.startswith("browse:"):
        _, mtype, page = data.split(":"); page = int(page)
        files = await list_files_for_type(mtype)
        if not files:
            await cq.answer(f"📭 {mtype} 目录为空", show_alert=True); return
        await cq.message.edit_text(text_file_list(mtype, page, files),
                                   reply_markup=kb_file_list(mtype, page, files))
        await cq.answer()

    elif data.startswith("finfo:"):
        fid = int(data.split(":")[1])
        p   = _lookup_path(fid)
        if not p:
            await cq.answer("❌ 文件不存在", show_alert=True); return
        mtype = next(
            (mt for mt, base in MEDIA_DIRS.items()
             if base in p.parents or base == p.parent.parent),
            "document",
        )
        files = await list_files_for_type(mtype)
        page  = next((i // PAGE_SIZE for i, (f_id, _, _, _) in enumerate(files) if f_id == fid), 0)
        await cq.message.edit_text(await text_file_info(fid),
                                   reply_markup=kb_file_info(fid, mtype, page))
        await cq.answer()

    elif data.startswith("finfo_s:"):
        parts   = data.split(":", 2)
        fid     = int(parts[1])
        keyword = parts[2] if len(parts) > 2 else ""
        p = _lookup_path(fid)
        if not p:
            await cq.answer("❌ 文件不存在", show_alert=True); return
        mtype = next(
            (mt for mt, base in MEDIA_DIRS.items()
             if base in p.parents or base == p.parent.parent),
            "document",
        )
        await cq.message.edit_text(
            await text_file_info(fid),
            reply_markup=kb_file_info(fid, mtype, 0, back_search=keyword),
        )
        await cq.answer()

    elif data.startswith("search_back:"):
        keyword = data.split(":", 1)[1]
        rows    = await async_db_search(keyword)
        await cq.message.edit_text(
            text_search_results(keyword, rows, 0),
            reply_markup=kb_search_results(rows, keyword, 0),
        )
        await cq.answer()

    elif data.startswith("search:"):
        parts   = data.split(":")
        keyword = parts[1]; page = int(parts[2])
        rows    = await async_db_search(keyword)
        await cq.message.edit_text(
            text_search_results(keyword, rows, page),
            reply_markup=kb_search_results(rows, keyword, page),
        )
        await cq.answer()

    elif data.startswith("fsend:"):
        fid = int(data.split(":")[1])
        p   = _lookup_path(fid)
        if not p:
            await cq.answer("❌ 文件不存在", show_alert=True); return

        exists, p_size = await asyncio.to_thread(lambda: (p.exists(), p.stat().st_size if p.exists() else 0))
        if not exists:
            await cq.answer("❌ 本地物理文件已被删除", show_alert=True); return

        await cq.answer("📤 开始回传…")
        status      = await cq.message.reply_text(
            f"📤 准备回传\n`{p.name}`  ({fmt_size(p_size)})"
        )
        progress_cb = make_upload_progress(status, p.name, p_size)

        ext = p.suffix.lower()
        try:
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                sent = await cq.message.reply_photo(str(p), progress=progress_cb)
            elif ext in (".mp4", ".mov", ".avi", ".mkv"):
                sent = await cq.message.reply_video(str(p), progress=progress_cb)
            elif ext in (".mp3", ".m4a", ".flac", ".aac"):
                sent = await cq.message.reply_audio(str(p), progress=progress_cb)
            elif ext in (".ogg", ".oga"):
                sent = await cq.message.reply_voice(str(p), progress=progress_cb)
            elif ext in (".gif",):
                sent = await cq.message.reply_animation(str(p), progress=progress_cb)
            else:
                sent = await cq.message.reply_document(str(p), progress=progress_cb)
            await status.delete()
            logger.info(f"📤 回传成功 {p.name} → msg_id={sent.id}")
        except Exception as exc:
            logger.error(f"回传失败 {p.name}: {exc}")
            await status.edit_text(f"❌ **回传失败**\n`{exc}`")

    elif data.startswith("fdel_ask:"):
        _, fid, mtype, page = data.split(":"); fid = int(fid); page = int(page)
        p = _lookup_path(fid)
        if not p:
            await cq.answer("❌ 文件不存在", show_alert=True); return
        exists, p_size = await asyncio.to_thread(lambda: (p.exists(), p.stat().st_size if p.exists() else 0))
        if not exists:
            await cq.answer("❌ 文件物理路径已不存在", show_alert=True); return
        await cq.message.edit_text(
            f"🗑️ **确认删除？**\n\n"
            f"📄 `{p.name}`\n"
            f"📦 {fmt_size(p_size)}\n"
            f"📂 `{p.parent}`\n\n"
            f"⚠️ 此操作**不可恢复**！",
            reply_markup=kb_file_del_confirm(fid, mtype, page),
        )
        await cq.answer()

    elif data.startswith("fdel_do:"):
        _, fid, mtype, page = data.split(":"); fid = int(fid); page = int(page)
        res = await asyncio.to_thread(_delete_single_file_sync, fid)
        if not res:
            await cq.answer("❌ 文件已不存在", show_alert=True)
            files = await list_files_for_type(mtype)
            await cq.message.edit_text(text_file_list(mtype, page, files),
                                       reply_markup=kb_file_list(mtype, page, files))
            return
        name_del, size_del = res
        await cq.answer(f"✅ 已删除 {name_del}")
        files   = await list_files_for_type(mtype)
        total_p = max(1, (len(files) + PAGE_SIZE - 1) // PAGE_SIZE)
        page    = min(page, total_p - 1)
        if files:
            await cq.message.edit_text(text_file_list(mtype, page, files),
                                       reply_markup=kb_file_list(mtype, page, files))
        else:
            await cq.message.edit_text(
                f"✅ **已删除** `{name_del}`\n\n📭 {mtype} 目录现在为空。",
                reply_markup=kb_back("menu:browse"),
            )

    elif data == "menu:delete":
        await cq.message.edit_text(await text_delete_select(), reply_markup=await kb_batch_type_select())
        await cq.answer()

    elif data.startswith("bdel_ask:"):
        mtype = data.split(":", 1)[1]
        if mtype == "ALL":
            _, tf, ts = await calc_stats()
            desc = f"**全部** {tf} 个文件  {fmt_size(ts)}"
        else:
            per, _, _ = await calc_stats()
            cnt, size = per.get(mtype, (0, 0))
            desc = f"{media_emoji(mtype)} **{mtype}** {cnt} 个  {fmt_size(size)}"
        await cq.message.edit_text(
            f"🗑️ **批量删除确认**\n\n即将删除：{desc}\n\n⚠️ **永久删除，不可恢复！**",
            reply_markup=kb_batch_del_confirm(mtype),
        )
        await cq.answer()

    elif data.startswith("bdel_do:"):
        mtype   = data.split(":", 1)[1]
        deleted_cnt, deleted_size = await asyncio.to_thread(_batch_delete_sync, mtype)
        label = "全部" if mtype == "ALL" else mtype
        logger.info(f"🗑️ 批量删除 [{label}] {deleted_cnt} 个  {fmt_size(deleted_size)}")
        await cq.message.edit_text(
            f"✅ **批量删除完成**\n\n"
            f"🗂️ 范围：**{label}**\n"
            f"📄 已删除：**{deleted_cnt}** 个文件\n"
            f"💾 释放空间：**{fmt_size(deleted_size)}**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🗑️ 继续删除", callback_data="menu:delete"),
                InlineKeyboardButton("🏠 主菜单",   callback_data="menu:home"),
            ]]),
        )
        await cq.answer(f"✅ 已删除 {deleted_cnt} 个文件", show_alert=True)
    else:
        await cq.answer("未知操作")

# ══════════════════════════════════════════════
#  核心：媒体下载
# ══════════════════════════════════════════════
MEDIA_FILTER = (
    filters.photo | filters.video | filters.audio | filters.voice |
    filters.document | filters.sticker | filters.animation | filters.video_note
)

@bot.on_message(MEDIA_FILTER & (filters.private | filters.group))
async def handle_media(_client: Client, msg: Message):
    uid = _uid(msg)
    if not is_allowed(uid): return

    media_type, file_name = detect_media(msg)
    if media_type is None: return

    if not ENABLED_TYPES.get(media_type, True):
        await msg.reply_text(
            f"{media_emoji(media_type)} **{media_type}** 类型已停用。",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔧 类型开关", callback_data="menu:types")
            ]]),
        )
        return

    safe_name  = "".join(c if c not in r'\/:*?"<>|' else "_" for c in file_name)
    save_dir   = get_save_dir(media_type)
    save_path  = safe_path(save_dir, safe_name)
    file_size  = get_file_size(msg)
    em         = media_emoji(media_type)

    status      = await msg.reply_text(
        f"{em} 准备下载{f'  ({fmt_size(file_size)})' if file_size else ''}\n`{safe_name}` ..."
    )
    progress_cb = make_progress(status, safe_name, media_type, file_size)

    t0 = time.monotonic()
    try:
        # 【⚡优化】限流信号量，确保下载线程不会无节制占满带宽与内存
        async with get_semaphore():
            await msg.download(file_name=str(save_path), progress=progress_cb)
    except Exception as exc:
        logger.error(f"下载失败 [{media_type}] {safe_name}: {exc}")
        await status.edit_text(f"❌ **下载失败**\n`{exc}`")
        return

    elapsed  = time.monotonic() - t0
    act_size = await asyncio.to_thread(lambda: save_path.stat().st_size if save_path.exists() else 0)
    avg_spd  = act_size / elapsed if elapsed > 0 else 0

    fid = await async_db_register(save_path, media_type, uid)
    logger.info(
        f"✅ [{media_type}] {save_path.name} fid={fid} "
        f"({fmt_size(act_size)}, {fmt_speed(avg_spd)}, {elapsed:.1f}s)"
    )

    await status.edit_text(
        f"{em} **下载完成！**\n\n"
        f"📝 `{save_path.name}`\n"
        f"📦 {fmt_size(act_size)}\n"
        f"⚡ 均速 {fmt_speed(avg_spd)}\n"
        f"⏱ 耗时 {elapsed:.1f}s\n"
        f"💾 `{save_path}`",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 查看详情", callback_data=f"finfo:{fid}"),
                InlineKeyboardButton("📤 回传文件", callback_data=f"fsend:{fid}"),
                InlineKeyboardButton("🗑️ 立即删除", callback_data=f"fdel_ask:{fid}:{media_type}:0"),
            ],
            [
                InlineKeyboardButton("📊 查看统计", callback_data="menu:status"),
                InlineKeyboardButton("🏠 主菜单",   callback_data="menu:home"),
            ],
        ]),
    )

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
    status    = await msg.reply_text(f"🌐 正在分析链接特征...\n`{url[:80]}`")
    last_text = [""]

    async def update_status(text: str):
        if text == last_text[0]: return
        last_text[0] = text
        try:
            await status.edit_text(text)
        except Exception:
            pass

    try:
        # 调用智能路由下载
        engine, files = await smart_download(
            url=url,
            media_roots=MEDIA_DIRS,
            status_cb=update_status
        )
    except Exception as exc:
        logger.error(f"引擎执行失败 [{url}]: {exc}")
        await status.edit_text(f"❌ **执行崩溃**\n`{exc}`", reply_markup=kb_back("menu:home"))
        return

    if not files:
        await status.edit_text(f"📭 引擎 `{engine}` 运行结束，未获取到任何媒体文件。")
        return

    # 结果入库并生成报告
    lines = [f"✅ **{engine} 下载完成！**\n", f"🌐 `{url[:60]}`\n"]
    
    video_cnt = photo_cnt = audio_cnt = 0
    for p in files:
        if not p.exists(): continue
        
        # 根据后缀判断媒体类型并入库
        ext = p.suffix.lower()
        if ext in (".mp4", ".mkv", ".webm"):
            mtype = "video"
            video_cnt += 1
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            mtype = "photo"
            photo_cnt += 1
        elif ext in (".mp3", ".m4a", ".flac"):
            mtype = "audio"
            audio_cnt += 1
        else:
            mtype = "document"
            
        await async_db_register(p, mtype, uid)

    if photo_cnt: lines.append(f"  🖼️ 图片：**{photo_cnt}** 个")
    if video_cnt: lines.append(f"  🎬 视频：**{video_cnt}** 个")
    if audio_cnt: lines.append(f"  🎵 音频：**{audio_cnt}** 个")
    
    # 动态构建浏览按钮
    type_buttons = []
    if photo_cnt: type_buttons.append(InlineKeyboardButton("🖼️ 浏览图片", callback_data="browse:photo:0"))
    if video_cnt: type_buttons.append(InlineKeyboardButton("🎬 浏览视频", callback_data="browse:video:0"))
    
    kb_rows = [type_buttons] if type_buttons else []
    kb_rows.append([
        InlineKeyboardButton("📊 查看统计", callback_data="menu:status"),
        InlineKeyboardButton("🏠 主菜单",   callback_data="menu:home"),
    ])

    await status.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(kb_rows)
    )
    
# ══════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════
if __name__ == "__main__":
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    db_init()
    db_load_registry()

    logger.info(f"📁 下载目录：{DOWNLOAD_ROOT.resolve()}")
    logger.info(f"💾 数据库：{DB_PATH.resolve()}")
    logger.info(f"📋 已加载历史记录：{len(_FILE_REGISTRY)} 条")
    logger.info(f"👤 白名单：{'全部用户' if not ALLOWED_USERS else ALLOWED_USERS}")
    logger.info(f"⚡ 并发限制：最大支持 {CONCURRENT_DOWNLOADS} 个任务同时下载")
    logger.info("🤖 Bot 启动（全异步线程优化版 · 极致丝滑）…")
    bot.run()

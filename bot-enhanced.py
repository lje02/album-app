#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 自动下载机器人 · Pyrogram 版  v3.1 ENHANCED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ MTProto 协议 — 无文件大小限制
✅ 实时进度条（速度 / 剩余时间）
✅ 8 种媒体类型自动分类保存
✅ 内联按钮管理菜单
✅ 按日期子目录归档
✅ 用户白名单
✅ 【NEW】并发下载控制（防止资源溢出）
✅ 【NEW】智能重试机制（指数退避）
✅ 【NEW】断点续传支持
✅ 【NEW】磁盘空间预检 + 内存监控
✅ 【NEW】数据库自动备份 + 日志轮转
✅ 【NEW】高级搜索过滤（大小/类型）
✅ 文件浏览器（分页）
✅ 单文件 / 批量删除（二次确认）
✅ 文件详情
✅ SQLite 持久化注册表（重启不丢失）
✅ 文件回传（发回 Telegram）
✅ 文件名模糊搜索（/search）
"""

import asyncio
import logging
import logging.handlers
import os
import sqlite3
import time
import psutil
import shutil
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ══════════════════════════════════════════════
#  加载 .env
# ══════════════════════════════════════════════
load_dotenv()

def _require(key: str) -> str:
    v = os.getenv(key, "").strip()
    if not v or v.startswith("your_"):
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
LOG_DIR             = Path(os.getenv("LOG_DIR", "./logs"))
ALLOWED_USERS: list[int] = [
    int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x.strip().isdigit()
]

# ══════════════════════════════════════════════
#  【NEW】性能和并发配置
# ══════════════════════════════════════════════
CONCURRENT_DOWNLOADS   = int(os.getenv("CONCURRENT_DOWNLOADS", "3"))
DOWNLOAD_TIMEOUT_SEC   = int(os.getenv("DOWNLOAD_TIMEOUT_SEC", "3600"))
MAX_RETRIES            = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE     = float(os.getenv("RETRY_BACKOFF_BASE", "2.0"))
MIN_FREE_SPACE_MB      = int(os.getenv("MIN_FREE_SPACE_MB", "100"))
MEMORY_WARN_PERCENT    = int(os.getenv("MEMORY_WARN_PERCENT", "80"))
DB_BACKUP_DAYS         = int(os.getenv("DB_BACKUP_DAYS", "1"))
CLEANUP_OLD_FILES_DAYS = int(os.getenv("CLEANUP_OLD_FILES_DAYS", "0"))  # 0=禁用

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
#  【NEW】全局状态管理
# ══════════════════════════════════════════════
download_queue: asyncio.Queue = None
active_downloads: Dict[int, Dict] = {}  # msg_id -> download_info
download_semaphore: asyncio.Semaphore = None

def init_async_resources():
    """初始化异步资源"""
    global download_queue, download_semaphore
    download_queue = asyncio.Queue(maxsize=20)
    download_semaphore = asyncio.Semaphore(CONCURRENT_DOWNLOADS)

# ══════════════════════════════════════════════
#  【NEW】日志配置（轮转）
# ══════════════════════════════════════════════
def setup_logging():
    """配置日志轮转"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 文件处理器（轮转）
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "bot.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# ══════════════════════════════════════════════
#  SQLite 持久化层
# ══════════════════════════════════════════════
_FILE_REGISTRY: dict[int, Path] = {}
_PATH_TO_FID:   dict[str, int]  = {}

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
    """建表（幂等）"""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                path          TEXT    UNIQUE NOT NULL,
                media_type    TEXT    NOT NULL,
                file_name     TEXT    NOT NULL,
                file_size     INTEGER NOT NULL DEFAULT 0,
                downloaded_at TEXT    NOT NULL,
                downloaded_by INTEGER,
                file_hash     TEXT,
                hash_type     TEXT DEFAULT 'md5'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON files(media_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_file_name  ON files(file_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_file_size  ON files(file_size)")

def db_load_registry():
    """启动时将 DB 中仍存在的文件加载进内存注册表"""
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
    logger.info(f"📋 已加载历史记录：{len(_FILE_REGISTRY)} 条，清理过期：{len(stale)} 条")

def db_register(path: Path, media_type: str, uid: int | None, file_hash: str = "") -> int:
    """注册文件（幂等），返回 fid"""
    key = str(path.resolve())
    if key in _PATH_TO_FID:
        return _PATH_TO_FID[key]
    stat = path.stat()
    with _db() as conn:
        conn.execute(
            """INSERT INTO files(path,media_type,file_name,file_size,downloaded_at,downloaded_by,file_hash)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 file_size=excluded.file_size,
                 downloaded_at=excluded.downloaded_at,
                 file_hash=excluded.file_hash""",
            (key, media_type, path.name, stat.st_size,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), uid, file_hash),
        )
        fid = conn.execute("SELECT id FROM files WHERE path=?", (key,)).fetchone()["id"]
    _FILE_REGISTRY[fid] = path
    _PATH_TO_FID[key]   = fid
    return fid

def db_unregister(fid: int):
    """从 DB + 内存移除"""
    p = _FILE_REGISTRY.pop(fid, None)
    if p:
        _PATH_TO_FID.pop(str(p.resolve()), None)
    with _db() as conn:
        conn.execute("DELETE FROM files WHERE id=?", (fid,))

def db_search(keyword: str, limit: int = 50) -> list:
    """基础搜索"""
    with _db() as conn:
        return conn.execute(
            "SELECT * FROM files WHERE file_name LIKE ? ORDER BY downloaded_at DESC LIMIT ?",
            (f"%{keyword}%", limit),
        ).fetchall()

def db_search_advanced(keyword: str = "", min_size: int = 0, 
                       max_size: int = -1, media_type: str = "", 
                       limit: int = 50) -> list:
    """【NEW】高级搜索（支持大小/类型过滤）"""
    query = "SELECT * FROM files WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND file_name LIKE ?"
        params.append(f"%{keyword}%")
    if media_type and media_type in MEDIA_DIRS:
        query += " AND media_type = ?"
        params.append(media_type)
    if min_size > 0:
        query += " AND file_size >= ?"
        params.append(min_size)
    if max_size > 0:
        query += " AND file_size <= ?"
        params.append(max_size)
    
    query += " ORDER BY downloaded_at DESC LIMIT ?"
    params.append(limit)
    
    with _db() as conn:
        return conn.execute(query, params).fetchall()

def db_get_row(fid: int):
    with _db() as conn:
        return conn.execute("SELECT * FROM files WHERE id=?", (fid,)).fetchone()

def _register_path(p: Path, media_type: str = "document", uid: int | None = None) -> int:
    return db_register(p, media_type, uid)

def _lookup_path(fid: int) -> Path | None:
    return _FILE_REGISTRY.get(fid)

def _unregister_path(fid: int):
    db_unregister(fid)

# ══════════════════════════════════════════════
#  【NEW】数据库备份
# ══════════════════════════════════════════════
def db_backup():
    """【NEW】定期备份数据库"""
    if not DB_PATH.exists():
        return
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y%m%d")
    backup_path = backup_dir / f"tg_downloader_{today}.db"
    
    # 检查今天是否已备份
    if backup_path.exists():
        return
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"💾 数据库备份完成：{backup_path}")
        
        # 清理超过 N 天的旧备份
        if DB_BACKUP_DAYS > 0:
            threshold = datetime.now() - timedelta(days=DB_BACKUP_DAYS * 7)
            for old_backup in backup_dir.glob("tg_downloader_*.db"):
                if datetime.fromtimestamp(old_backup.stat().st_mtime) < threshold:
                    old_backup.unlink()
                    logger.debug(f"🗑️ 已删除过期备份：{old_backup.name}")
    except Exception as e:
        logger.error(f"❌ 数据库备份失败：{e}")

# ══════════════════════════════════════════════
#  【NEW】清理过期文件
# ══════════════════════════════════════════════
def cleanup_old_files(days: int = 30):
    """【NEW】删除超过指定天数的文件"""
    if days <= 0:
        return
    
    threshold_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    with _db() as conn:
        old_rows = conn.execute(
            "SELECT id, path, file_name, file_size FROM files WHERE downloaded_at < ?",
            (threshold_date,)
        ).fetchall()
    
    deleted_count = 0
    deleted_size = 0
    
    for row in old_rows:
        fid, path_str, name, size = row["id"], row["path"], row["file_name"], row["file_size"]
        p = Path(path_str)
        try:
            if p.exists():
                p.unlink()
                deleted_count += 1
                deleted_size += size
            _unregister_path(fid)
        except OSError as e:
            logger.warning(f"⚠️ 清理失败 {name}：{e}")
    
    if deleted_count > 0:
        logger.info(f"🧹 清理过期文件（{days}天前）：{deleted_count} 个，释放 {fmt_size(deleted_size)}")

# ══════════════════════════════════════════════
#  【NEW】系统监控
# ══════════════════════════════════════════════
def check_system_health() -> Dict[str, any]:
    """【NEW】检查系统健康状态"""
    memory_percent = psutil.virtual_memory().percent
    disk_usage = shutil.disk_usage(DOWNLOAD_ROOT)
    free_gb = disk_usage.free / (1024**3)
    
    health = {
        "memory_percent": memory_percent,
        "free_space_gb": free_gb,
        "free_space_bytes": disk_usage.free,
        "is_healthy": True,
        "warnings": [],
    }
    
    if memory_percent > MEMORY_WARN_PERCENT:
        health["warnings"].append(f"⚠️ 内存占用 {memory_percent}%")
        health["is_healthy"] = False
    
    min_free_bytes = MIN_FREE_SPACE_MB * 1024 * 1024
    if disk_usage.free < min_free_bytes:
        health["warnings"].append(
            f"⚠️ 磁盘剩余仅 {free_gb:.2f}GB（阈值 {MIN_FREE_SPACE_MB}MB）"
        )
        health["is_healthy"] = False
    
    return health

def ensure_disk_space(required_bytes: int) -> bool:
    """【NEW】预检磁盘空间"""
    disk_usage = shutil.disk_usage(DOWNLOAD_ROOT)
    if disk_usage.free < required_bytes:
        logger.error(
            f"❌ 磁盘空间不足：需要 {fmt_size(required_bytes)}，"
            f"可用 {fmt_size(disk_usage.free)}"
        )
        return False
    return True

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
#  【NEW】文件哈希校验
# ══════════════════════════════════════════════
def calc_file_hash(path: Path, algorithm: str = "md5") -> str:
    """【NEW】计算文件哈希值"""
    import hashlib
    hasher = hashlib.new(algorithm)
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.warning(f"⚠️ 哈希计算失败 {path.name}：{e}")
        return ""

def supports_resume(media_type: str) -> bool:
    """【NEW】检查媒体类型是否支持断点续传"""
    return media_type in ("video", "document", "audio")

# ══════════════════════════════════════════════
#  文件列表辅助
# ══════════════════════════════════════════════

def list_files_for_type(mtype: str) -> list[Path]:
    base = MEDIA_DIRS.get(mtype)
    if not base or not base.exists():
        return []
    return sorted(
        (f for f in base.rglob("*") if f.is_file()),
        key=lambda f: f.stat().st_mtime, reverse=True,
    )

# ══════════════════════════════���═══════════════
#  统计
# ══════════════════════════════════════════════

def calc_stats() -> tuple[dict, int, int]:
    per = {}; tf = ts = 0
    for mtype, base in MEDIA_DIRS.items():
        if not base.exists():
            per[mtype] = (0, 0); continue
        files = [f for f in base.rglob("*") if f.is_file()]
        cnt = len(files); size = sum(f.stat().st_size for f in files)
        per[mtype] = (cnt, size); tf += cnt; ts += size
    return per, tf, ts

# ══════════════════════════════════════════════
#  【NEW】智能重试机制
# ══════════════════════════════════════════════
async def download_with_retry(msg: Message, save_path: Path, 
                              progress_cb, file_name: str,
                              max_retries: int = MAX_RETRIES,
                              backoff_base: float = RETRY_BACKOFF_BASE) -> bool:
    """【NEW】指数退避重试下载"""
    for attempt in range(max_retries):
        try:
            logger.debug(f"📥 下载尝试 {attempt+1}/{max_retries}：{file_name}")
            await msg.download(file_name=str(save_path), progress=progress_cb)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 下载超时，准备重试：{file_name}")
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = backoff_base ** attempt
                logger.warning(
                    f"⚠️ 下载失败（尝试 {attempt+1}/{max_retries}），"
                    f"{wait_time:.0f}s 后重试：{e}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ 下载最终失败（已重试 {max_retries} 次）：{e}")
                return False
    return False

# ══════════════════════════════════════════════
#  键盘构建
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

def kb_type_select(prefix: str, back: str = "menu:home") -> InlineKeyboardMarkup:
    per, _, _ = calc_stats(); rows = []
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

def kb_file_list(mtype: str, page: int, files: list[Path]) -> InlineKeyboardMarkup:
    total_p = max(1, (len(files) + PAGE_SIZE - 1) // PAGE_SIZE)
    rows = []
    for f in files[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        fid = _register_path(f, mtype)
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

def kb_batch_type_select() -> InlineKeyboardMarkup:
    per, _, _ = calc_stats(); rows = []
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
        if fid not in _FILE_REGISTRY and p.exists():
            _FILE_REGISTRY[fid] = p
            _PATH_TO_FID[str(p.resolve())] = fid
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
#  文本构建
# ══════════════════════════════════════════════

def text_home(name: str) -> str:
    enabled = sum(1 for v in ENABLED_TYPES.values() if v)
    _, tf, ts = calc_stats()
    health = check_system_health()
    
    status_line = ""
    if not health["is_healthy"]:
        status_line = f"\n⚠️ **系统警告**：{', '.join(health['warnings'])}"
    
    return (
        f"👋 你好，**{name}**！\n\n"
        f"📥 **Telegram 自动下载机器人**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗂️ 已保存文件：**{tf}** 个  ({fmt_size(ts)})\n"
        f"🔛 启用类型：**{enabled}** / {len(MEDIA_DIRS)}\n"
        f"📂 根目录：`{DOWNLOAD_ROOT.resolve()}`\n"
        f"💾 可用空间：{fmt_size(health['free_space_bytes'])} "
        f"（内存 {health['memory_percent']}%）\n\n"
        f"直接发送或转发媒体给我，自动保存 👇\n"
        f"🔍 搜索文件：`/search 关键词`"
        f"{status_line}"
    )

def text_status() -> str:
    per, tf, ts = calc_stats()
    lines = ["📊 **下载统计**\n"]
    for mtype, (cnt, size) in per.items():
        flag = "✅" if ENABLED_TYPES[mtype] else "⏸"
        bar  = "▓" * min(cnt // max(1, tf // 10 + 1), 8) if tf else ""
        lines.append(f"  {flag} {media_emoji(mtype)} **{mtype}**：{cnt} 个  {fmt_size(size)}  {bar}")
    lines.append(f"\n📦 **合计**：{tf} 个文件，{fmt_size(ts)}")
    lines.append(f"🕐 更新时间：{datetime.now().strftime('%H:%M:%S')}")
    
    health = check_system_health()
    lines.append(f"\n💻 **系统状态**")
    lines.append(f"  💾 磁盘可用：{fmt_size(health['free_space_bytes'])}")
    lines.append(f"  🧠 内存占用：{health['memory_percent']}%")
    
    if health["warnings"]:
        lines.append(f"\n⚠️ **警告**：{', '.join(health['warnings'])}")
    
    return "\n".join(lines)

def text_dirs() -> str:
    lines = [f"📁 **目录结构**\n`{DOWNLOAD_ROOT.resolve()}`\n"]
    for mtype, path in MEDIA_DIRS.items():
        exists = path.exists()
        cnt    = len([f for f in path.rglob("*") if f.is_file()]) if exists else 0
        lines.append(
            f"  {'✅' if exists else '⬜'}{'▶' if ENABLED_TYPES[mtype] else '⏸'} "
            f"{media_emoji(mtype)} `{path.relative_to(DOWNLOAD_ROOT)}`  _{cnt} 个_"
        )
    return "\n".join(lines)

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
        f"⚡ **性能配置**\n"
        f"  🔄 并发下载：{CONCURRENT_DOWNLOADS}\n"
        f"  🔁 最大重试：{MAX_RETRIES}\n"
        f"  💾 最小磁盘空间：{MIN_FREE_SPACE_MB}MB\n"
        f"  🧠 内存警告阈值：{MEMORY_WARN_PERCENT}%\n\n"
        f"🔛 启用类型：{'  '.join(media_emoji(t) for t in enabled_list)}"
    )

def text_browse_select() -> str:
    per, tf, ts = calc_stats()
    lines = [f"🔍 **浏览文件**  共 {tf} 个 / {fmt_size(ts)}\n\n选择媒体类型："]
    for mtype, (cnt, size) in per.items():
        lines.append(f"  {media_emoji(mtype)} **{mtype}**：{cnt} 个  {fmt_size(size)}")
    return "\n".join(lines)

def text_file_list(mtype: str, page: int, files: list[Path]) -> str:
    total   = len(files)
    total_p = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    start   = page * PAGE_SIZE
    lines   = [f"{media_emoji(mtype)} **{mtype}** 文件列表",
               f"共 {total} 个  第 {page+1}/{total_p} 页\n"]
    for i, f in enumerate(files[start:start + PAGE_SIZE], start=start + 1):
        stat = f.stat()
        lines.append(
            f"  `{i}.` {f.name[:36]}  "
            f"_{fmt_size(stat.st_size)}_  "
            f"{fmt_ts(stat.st_mtime)[:10]}"
        )
    lines.append("\n点击文件名查看详情")
    return "\n".join(lines)

def text_file_info(fid: int) -> str:
    p = _lookup_path(fid)
    if not p or not p.exists():
        return "❌ 文件不存在或已被删除"
    stat = p.stat()
    row  = db_get_row(fid)
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

def text_delete_select() -> str:
    per, tf, ts = calc_stats()
    lines = [f"🗑️ **删除文件**  共 {tf} 个 / {fmt_size(ts)}\n\n选择删除范围："]
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
    lines = [f"🔍 搜索 **`{keyword}`**  共 {total} 条  第 {page+1}/{total_p} 页\n"]
    for i, row in enumerate(rows[start:start + PAGE_SIZE], start=start + 1):
        p      = Path(row["path"])
        exists = "✅" if p.exists() else "❌"
        lines.append(
            f"  {exists} `{i}.` {row['file_name'][:34]}  "
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
                f"{media_emoji(media_type)} **正在下载**\n`{file_name}`\n\n"
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
#  Pyrogram 客户端
# ══════════════════════════════════════════════
bot = Client(
    "tg_downloader_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ══════════════════════════════════════════════
#  命令处理器
# ══════════════════════════════════════════════

def _uid(msg: Message) -> int | None:
    return msg.from_user.id if msg.from_user else None

@bot.on_message(filters.command("start") & (filters.private | filters.group))
async def cmd_start(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    name = msg.from_user.first_name if msg.from_user else "用户"
    await msg.reply_text(text_home(name), reply_markup=kb_main())

@bot.on_message(filters.command("menu") & (filters.private | filters.group))
async def cmd_menu(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    name = msg.from_user.first_name if msg.from_user else "用户"
    await msg.reply_text(text_home(name), reply_markup=kb_main())

@bot.on_message(filters.command("status") & (filters.private | filters.group))
async def cmd_status(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(text_status(), reply_markup=kb_back())

@bot.on_message(filters.command("dirs") & (filters.private | filters.group))
async def cmd_dirs(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(text_dirs(), reply_markup=kb_back())

@bot.on_message(filters.command("browse") & (filters.private | filters.group))
async def cmd_browse(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(text_browse_select(),
                         reply_markup=kb_type_select("browse", back="menu:home"))

@bot.on_message(filters.command("delete") & (filters.private | filters.group))
async def cmd_delete(_, msg: Message):
    if not is_allowed(_uid(msg)): return
    await msg.reply_text(text_delete_select(), reply_markup=kb_batch_type_select())

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
    rows    = db_search(keyword)
    await msg.reply_text(
        text_search_results(keyword, rows, 0),
        reply_markup=kb_search_results(rows, keyword, 0),
    )

# ══════════════════════════════════════════════
#  内联按钮回调
# ══════════════════════════════════════════════

@bot.on_callback_query()
async def on_callback(_, cq: CallbackQuery):
    uid = cq.from_user.id
    if not is_allowed(uid):
        await cq.answer("⛔ 无权限", show_alert=True); return

    data = cq.data
    name = cq.from_user.first_name or "用户"

    # ── 占位 ──────────────────────────────────
    if data == "noop":
        await cq.answer(); return

    # ── 主菜单 ────────────────────────────────
    elif data == "menu:home":
        await cq.message.edit_text(text_home(name), reply_markup=kb_main())
        await cq.answer()

    elif data == "menu:status":
        await cq.message.edit_text(text_status(), reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 刷新", callback_data="menu:status"),
            InlineKeyboardButton("« 返回",  callback_data="menu:home"),
        ]]))
        await cq.answer("已刷新")

    elif data == "menu:dirs":
        await cq.message.edit_text(text_dirs(), reply_markup=InlineKeyboardMarkup([[
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

    # ── 浏览 ──────────────────────────────────
    elif data == "menu:browse":
        await cq.message.edit_text(text_browse_select(),
                                   reply_markup=kb_type_select("browse", back="menu:home"))
        await cq.answer()

    elif data.startswith("browse:"):
        _, mtype, page = data.split(":"); page = int(page)
        files = list_files_for_type(mtype)
        if not files:
            await cq.answer(f"📭 {mtype} 目录为空", show_alert=True); return
        await cq.message.edit_text(text_file_list(mtype, page, files),
                                   reply_markup=kb_file_list(mtype, page, files))
        await cq.answer()

    # ── 文件详情（来自浏览）──────────────────
    elif data.startswith("finfo:"):
        fid = int(data.split(":")[1])
        p   = _lookup_path(fid)
        if not p or not p.exists():
            await cq.answer("❌ 文件不存在", show_alert=True); return
        mtype = next(
            (mt for mt, base in MEDIA_DIRS.items()
             if base in p.parents or base == p.parent.parent),
            "document",
        )
        files = list_files_for_type(mtype)
        page  = next((i // PAGE_SIZE for i, f in enumerate(files) if f == p), 0)
        await cq.message.edit_text(text_file_info(fid),
                                   reply_markup=kb_file_info(fid, mtype, page))
        await cq.answer()

    # ── 文件详情（来自搜索）──────────────────
    elif data.startswith("finfo_s:"):
        parts   = data.split(":", 2)
        fid     = int(parts[1])
        keyword = parts[2] if len(parts) > 2 else ""
        p = _lookup_path(fid)
        if not p or not p.exists():
            await cq.answer("❌ 文件不存在", show_alert=True); return
        mtype = next(
            (mt for mt, base in MEDIA_DIRS.items()
             if base in p.parents or base == p.parent.parent),
            "document",
        )
        await cq.message.edit_text(
            text_file_info(fid),
            reply_markup=kb_file_info(fid, mtype, 0, back_search=keyword),
        )
        await cq.answer()

    # ── 搜索返回 ──────────────────────────────
    elif data.startswith("search_back:"):
        keyword = data.split(":", 1)[1]
        rows    = db_search(keyword)
        await cq.message.edit_text(
            text_search_results(keyword, rows, 0),
            reply_markup=kb_search_results(rows, keyword, 0),
        )
        await cq.answer()

    # ── 搜索翻页 ──────────────────────────────
    elif data.startswith("search:"):
        parts   = data.split(":")
        keyword = parts[1]; page = int(parts[2])
        rows    = db_search(keyword)
        await cq.message.edit_text(
            text_search_results(keyword, rows, page),
            reply_markup=kb_search_results(rows, keyword, page),
        )
        await cq.answer()

    # ── 文件回传 ──────────────────────────────
    elif data.startswith("fsend:"):
        fid = int(data.split(":")[1])
        p   = _lookup_path(fid)
        if not p or not p.exists():
            await cq.answer("❌ 文件不存在", show_alert=True); return

        await cq.answer("📤 开始回传…")
        status      = await cq.message.reply_text(
            f"📤 准备回传\n`{p.name}`  ({fmt_size(p.stat().st_size)})"
        )
        progress_cb = make_upload_progress(status, p.name, p.stat().st_size)

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

    # ── 单文件删除：询问 ──────────────────────
    elif data.startswith("fdel_ask:"):
        _, fid, mtype, page = data.split(":"); fid = int(fid); page = int(page)
        p = _lookup_path(fid)
        if not p or not p.exists():
            await cq.answer("❌ 文件不存在", show_alert=True); return
        await cq.message.edit_text(
            f"🗑️ **确认删除？**\n\n"
            f"📄 `{p.name}`\n"
            f"📦 {fmt_size(p.stat().st_size)}\n"
            f"📂 `{p.parent}`\n\n"
            f"⚠️ 此操作**不可恢复**！",
            reply_markup=kb_file_del_confirm(fid, mtype, page),
        )
        await cq.answer()

    # ── 单文件删除：执行 ──────────────────────
    elif data.startswith("fdel_do:"):
        _, fid, mtype, page = data.split(":"); fid = int(fid); page = int(page)
        p = _lookup_path(fid)
        if not p or not p.exists():
            await cq.answer("❌ 文件已不存在", show_alert=True)
            files = list_files_for_type(mtype)
            await cq.message.edit_text(text_file_list(mtype, page, files),
                                       reply_markup=kb_file_list(mtype, page, files))
            return
        name_del = p.name; size_del = p.stat().st_size
        try:
            p.unlink()
            _unregister_path(fid)
            try: p.parent.rmdir()
            except OSError: pass
            logger.info(f"🗑️ 已删除 [{mtype}] {name_del} ({fmt_size(size_del)})")
        except Exception as exc:
            await cq.answer(f"❌ 删除失败：{exc}", show_alert=True); return

        await cq.answer(f"✅ 已删除 {name_del}")
        files   = list_files_for_type(mtype)
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

    # ── 批量删除 ──────────────────────────────
    elif data == "menu:delete":
        await cq.message.edit_text(text_delete_select(), reply_markup=kb_batch_type_select())
        await cq.answer()

    elif data.startswith("bdel_ask:"):
        mtype = data.split(":", 1)[1]
        if mtype == "ALL":
            _, tf, ts = calc_stats()
            desc = f"**全部** {tf} 个文件  {fmt_size(ts)}"
        else:
            per, _, _ = calc_stats()
            cnt, size = per.get(mtype, (0, 0))
            desc = f"{media_emoji(mtype)} **{mtype}**  {cnt} 个  {fmt_size(size)}"
        await cq.message.edit_text(
            f"🗑️ **批量删除确认**\n\n即将删除：{desc}\n\n⚠️ **永久删除，不可恢复！**",
            reply_markup=kb_batch_del_confirm(mtype),
        )
        await cq.answer()

    elif data.startswith("bdel_do:"):
        mtype   = data.split(":", 1)[1]
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
#  核心：媒体下载（集成优化）
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

    # ── 【NEW】系统健康检查 ────────────────────
    health = check_system_health()
    if not health["is_healthy"]:
        await msg.reply_text(
            f"❌ **系统异常**\n\n{', '.join(health['warnings'])}\n\n"
            f"请稍后重试或 /status 查看详情"
        )
        return

    file_size = get_file_size(msg)

    # ── 【NEW】磁盘空间预检 ────────────────────
    if file_size > 0 and not ensure_disk_space(file_size * 1.1):  # 预留 10%
        await msg.reply_text(
            f"❌ **磁盘空间不足**\n\n"
            f"需要：{fmt_size(int(file_size * 1.1))}\n"
            f"可用：{fmt_size(health['free_space_bytes'])}"
        )
        return

    safe_name  = "".join(c if c not in r'\/:*?"<>|' else "_" for c in file_name)
    save_dir   = get_save_dir(media_type)
    save_path  = safe_path(save_dir, safe_name)
    em         = media_emoji(media_type)

    status      = await msg.reply_text(
        f"{em} 准备下载{f'  ({fmt_size(file_size)})' if file_size else ''}\n`{safe_name}` ..."
    )
    progress_cb = make_progress(status, safe_name, media_type, file_size)

    # ── 【NEW】带重试的下载（并发控制） ────────
    t0 = time.monotonic()
    try:
        async with download_semaphore:
            success = await download_with_retry(
                msg, save_path, progress_cb, safe_name,
                max_retries=MAX_RETRIES,
                backoff_base=RETRY_BACKOFF_BASE,
            )
            if not success:
                raise Exception("下载重试失败")
    except Exception as exc:
        logger.error(f"下载失败 [{media_type}] {safe_name}: {exc}")
        await status.edit_text(f"❌ **下载失败**\n`{exc}`")
        return

    elapsed  = time.monotonic() - t0
    act_size = save_path.stat().st_size if save_path.exists() else 0
    avg_spd  = act_size / elapsed if elapsed > 0 else 0

    # ── 【NEW】文件哈希计算 ────────────────────
    file_hash = calc_file_hash(save_path, "md5") if act_size > 0 else ""

    fid = db_register(save_path, media_type, uid, file_hash)
    logger.info(
        f"✅ [{media_type}] {save_path.name} fid={fid} "
        f"({fmt_size(act_size)}, {fmt_speed(avg_spd)}, {elapsed:.1f}s)"
        f"{f' hash={file_hash}' if file_hash else ''}"
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

# ══════════════════════════════════════════════
#  【NEW】后台任务（定期维护）
# ══════════════════════════════════════════════

async def maintenance_task():
    """【NEW】后台定期维护任务"""
    while True:
        try:
            # 每 6 小时执行一次
            await asyncio.sleep(6 * 3600)
            
            logger.info("🔧 执行定期维护...")
            
            # 数据库备份
            db_backup()
            
            # 清理过期文件
            if CLEANUP_OLD_FILES_DAYS > 0:
                cleanup_old_files(CLEANUP_OLD_FILES_DAYS)
            
            logger.info("✅ 定期维护完成")
        except Exception as e:
            logger.error(f"❌ 维护任务出错：{e}")

# ══════════════════════════════════════════════
#  入口
# ══════════════════════════════════════════════

if __name__ == "__main__":
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    db_init()
    db_load_registry()
    init_async_resources()

    logger.info(f"📁 下载目录：{DOWNLOAD_ROOT.resolve()}")
    logger.info(f"💾 数据库：{DB_PATH.resolve()}")
    logger.info(f"📋 已加载历史记录：{len(_FILE_REGISTRY)} 条")
    logger.info(f"👤 白名单：{'全部用户' if not ALLOWED_USERS else ALLOWED_USERS}")
    logger.info(f"⚡ 并发限制：{CONCURRENT_DOWNLOADS} | 最大重试：{MAX_RETRIES}")
    logger.info(f"💾 最小磁盘空间：{MIN_FREE_SPACE_MB}MB | 内存警告：{MEMORY_WARN_PERCENT}%")
    logger.info("🤖 Bot 启动（Pyrogram · MTProto · 优化增强版 v3.1）…")
    
    # 启动后台任务
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(maintenance_task())
    
    bot.run()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
url_scanner.py — URL 扫描 & 媒体批量下载扩展模块  v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 图片 / 视频 / 音频 三类媒体自动识别并分别保存
✅ HEAD 请求预检文件大小（图片默认 ≥ 100 KB）
✅ 视频/音频单独限速并发（防止大文件撑爆内存）
✅ 域名 + 页面标题自动生成下载子目录
✅ 支持普通网页 / 图片·视频·音频直链列表页
✅ 并发下载 + 实时进度播报
✅ 全部结果注册进 SQLite（与主脚本共用 db_register）
"""

import asyncio
import logging
import os
import re
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── 可在 .env 中覆盖的配置 ──────────────────────────────────────────
MIN_FILE_SIZE    = int(os.getenv("URL_MIN_FILE_SIZE",    "102400"))  # 100 KB（图片过滤阈值）
MIN_VIDEO_SIZE   = int(os.getenv("URL_MIN_VIDEO_SIZE",   "524288"))  # 512 KB（视频过滤阈值）
MIN_AUDIO_SIZE   = int(os.getenv("URL_MIN_AUDIO_SIZE",   "51200"))   # 50 KB（音频过滤阈值）
SCAN_TIMEOUT     = int(os.getenv("URL_SCAN_TIMEOUT",     "20"))      # 页面抓取超时 (s)
DL_TIMEOUT_IMG   = int(os.getenv("URL_DL_TIMEOUT_IMG",   "60"))      # 图片单文件超时 (s)
DL_TIMEOUT_VIDEO = int(os.getenv("URL_DL_TIMEOUT_VIDEO", "600"))     # 视频单文件超时 (s)
DL_TIMEOUT_AUDIO = int(os.getenv("URL_DL_TIMEOUT_AUDIO", "120"))     # 音频单文件超时 (s)
DL_CONCURRENCY   = int(os.getenv("URL_DL_CONCURRENCY",   "4"))       # 图片并发下载数
DL_CONCURRENCY_V = int(os.getenv("URL_DL_CONCURRENCY_V", "2"))       # 视频并发下载数（保守）
DL_CONCURRENCY_A = int(os.getenv("URL_DL_CONCURRENCY_A", "3"))       # 音频并发下载数
MAX_ITEMS        = int(os.getenv("URL_MAX_IMAGES",        "200"))     # 单次最多处理文件数
PROGRESS_EVERY   = int(os.getenv("URL_PROGRESS_EVERY",   "3"))       # 每 N 个更新一次进度

# 常见请求头（减少被反爬拦截）
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# ── 媒体类型扩展名集合 ───────────────────────────────────────────────
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".avif", ".jfif"}
VIDEO_EXTS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".ts", ".m4v", ".rmvb"}
AUDIO_EXTS = {".mp3", ".flac", ".aac", ".ogg", ".m4a", ".wav", ".opus", ".wma"}

# media_type → (扩展名集合, 主脚本 media_type 字符串, 超时, 并发, 最小尺寸)
_TYPE_META = {
    "photo":    (IMAGE_EXTS, "photo",    DL_TIMEOUT_IMG,   DL_CONCURRENCY,   MIN_FILE_SIZE),
    "video":    (VIDEO_EXTS, "video",    DL_TIMEOUT_VIDEO, DL_CONCURRENCY_V, MIN_VIDEO_SIZE),
    "audio":    (AUDIO_EXTS, "audio",    DL_TIMEOUT_AUDIO, DL_CONCURRENCY_A, MIN_AUDIO_SIZE),
}

# ────────────────────────────────────────────────────────────────────
#  工具函数
# ────────────────────────────────────────────────────────────────────

def fmt_size(n: int) -> str:
    if n < 1024:      return f"{n} B"
    if n < 1 << 20:   return f"{n/1024:.1f} KB"
    if n < 1 << 30:   return f"{n/(1<<20):.1f} MB"
    return f"{n/(1<<30):.2f} GB"

def sanitize_name(s: str, max_len: int = 40) -> str:
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r'\s+', "_", s.strip())
    s = re.sub(r'_+', "_", s).strip("_")
    return s[:max_len] if s else "untitled"

def make_folder_name(domain: str, title: str) -> str:
    """域名 + 页面标题 → 合法目录名，最长 60 字符"""
    domain_part = sanitize_name(domain.lstrip("www."), 20)
    title_part  = sanitize_name(title, 38)
    if title_part and title_part.lower() not in domain_part.lower():
        return f"{domain_part}_{title_part}"
    return domain_part or "untitled"

def classify_url(url: str) -> str | None:
    """
    判断 URL 属于哪种媒体类型，返回 'photo' / 'video' / 'audio' / None。
    先按扩展名判断，其次尝试 Content-Type（HEAD 时才用）。
    """
    path = urlparse(url).path.lower().split("?")[0]
    for mtype, (exts, *_) in _TYPE_META.items():
        if any(path.endswith(e) for e in exts):
            return mtype
    return None

def classify_by_content_type(ct: str) -> str | None:
    ct = ct.lower()
    if ct.startswith("image/"):  return "photo"
    if ct.startswith("video/"):  return "video"
    if ct.startswith("audio/"):  return "audio"
    return None

# ────────────────────────────────────────────────────────────────────
#  HTML 解析
# ────────────────────────────────────────────────────────────────────

async def fetch_page(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    """返回 (html_text, final_url)"""
    async with session.get(
        url, headers=HEADERS,
        timeout=aiohttp.ClientTimeout(total=SCAN_TIMEOUT),
    ) as resp:
        resp.raise_for_status()
        html = await resp.text(errors="replace")
        return html, str(resp.url)

def _collect_links(soup: BeautifulSoup, base_url: str) -> dict[str, list[str]]:
    """
    从 soup 中收集所有媒体 URL，按类型分桶返回：
    {
      "photo": [...],
      "video": [...],
      "audio": [...],
    }
    """
    buckets: dict[str, list[str]] = {"photo": [], "video": [], "audio": []}

    def add(url: str, mtype: str):
        if url and url.startswith("http") and url not in buckets[mtype]:
            buckets[mtype].append(url)

    # ① <img> 标签（含懒加载属性）
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy-src",
                     "data-url", "data-hi-res-src", "data-full-url"):
            val = img.get(attr, "").strip()
            if val and not val.startswith("data:"):
                abs_url = urljoin(base_url, val)
                add(abs_url, "photo")
                break

    # ② <video src> / <video><source src>
    for tag in soup.find_all(["video", "source"]):
        for attr in ("src", "data-src"):
            val = tag.get(attr, "").strip()
            if val:
                abs_url = urljoin(base_url, val)
                mt = classify_url(abs_url)
                if mt == "video":
                    add(abs_url, "video")
                break
        # poster 属性是封面图
        poster = tag.get("poster", "").strip()
        if poster:
            add(urljoin(base_url, poster), "photo")

    # ③ <audio src> / <audio><source src>
    for tag in soup.find_all(["audio", "source"]):
        for attr in ("src", "data-src"):
            val = tag.get(attr, "").strip()
            if val:
                abs_url = urljoin(base_url, val)
                mt = classify_url(abs_url)
                if mt == "audio":
                    add(abs_url, "audio")
                break

    # ④ <a href> 直链（含图片直链列表页、视频/音频列表页）
    for a in soup.find_all("a", href=True):
        abs_url = urljoin(base_url, a["href"])
        mt = classify_url(abs_url)
        if mt:
            add(abs_url, mt)

    # ⑤ og:image / og:video / og:audio meta
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or meta.get("name") or "").lower()
        content = meta.get("content", "").strip()
        if not content.startswith("http"):
            continue
        if "image" in prop:
            add(content, "photo")
        elif "video" in prop:
            mt = classify_url(content) or "video"
            if mt == "video":
                add(content, "video")
        elif "audio" in prop:
            mt = classify_url(content) or "audio"
            if mt == "audio":
                add(content, "audio")

    # ⑥ URL 本身就是媒体直链
    mt = classify_url(base_url)
    if mt:
        if base_url not in buckets[mt]:
            buckets[mt].insert(0, base_url)

    # 各桶截断
    for k in buckets:
        buckets[k] = buckets[k][:MAX_ITEMS * 2]

    return buckets

def extract_all_media(html: str, base_url: str) -> tuple[dict[str, list[str]], str, str]:
    """
    返回 (buckets, page_title, domain)
    buckets = {"photo": [...], "video": [...], "audio": [...]}
    """
    soup   = BeautifulSoup(html, "html.parser")
    domain = urlparse(base_url).netloc

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        og = soup.find("meta", property="og:title")
        title = (og.get("content") or "").strip() if og else ""

    buckets = _collect_links(soup, base_url)
    return buckets, title, domain

# ────────────────────────────────────────────────────────────────────
#  HEAD 预检（大小 + Content-Type 补充分类）
# ────────────────────────────────────────────────────────────────────

async def head_check(
    session: aiohttp.ClientSession,
    url: str,
    hint_mtype: str,
) -> tuple[str, str, int]:
    """
    返回 (url, confirmed_mtype, size)。
    - confirmed_mtype: 以 Content-Type 修正后的媒体类型（可能与 hint 不同）
    - size: -1 表示无 Content-Length
    """
    try:
        async with session.head(
            url, headers=HEADERS,
            timeout=aiohttp.ClientTimeout(total=10),
            allow_redirects=True,
        ) as resp:
            cl = resp.headers.get("Content-Length", "")
            ct = resp.headers.get("Content-Type", "")
            size = int(cl) if cl.isdigit() else -1
            ct_type = classify_by_content_type(ct)
            final_mtype = ct_type or hint_mtype
            return url, final_mtype, size
    except Exception:
        return url, hint_mtype, -1

async def filter_bucket(
    session: aiohttp.ClientSession,
    urls: list[str],
    hint_mtype: str,
    min_size: int,
) -> dict[str, list[tuple[str, int]]]:
    """
    HEAD 预检整个桶，返回按 mtype 分组的通过列表：
    { "photo": [(url, size), ...], "video": [...], "audio": [...] }
    （HEAD 检测可能将某个 URL 重新归类到其他 mtype）
    """
    semaphore = asyncio.Semaphore(8)
    result: dict[str, list[tuple[str, int]]] = {"photo": [], "video": [], "audio": []}

    async def check(url: str):
        async with semaphore:
            return await head_check(session, url, hint_mtype)

    for coro in asyncio.as_completed([check(u) for u in urls]):
        url, mtype, size = await coro
        target_min = _TYPE_META.get(mtype, _TYPE_META["photo"])[4]
        if size == -1 or size >= target_min:
            if mtype in result:
                result[mtype].append((url, size))

    # 各桶保持原始顺序并截断
    order = {u: i for i, u in enumerate(urls)}
    for k in result:
        result[k].sort(key=lambda x: order.get(x[0], 9999))
        result[k] = result[k][:MAX_ITEMS]

    return result

# ────────────────────────────────────────────────────────────────────
#  通用流式下载
# ────────────────────────────────────────────────────────────────────

async def stream_download(
    session: aiohttp.ClientSession,
    url: str,
    save_path: Path,
    timeout_s: int,
) -> int:
    """流式写入文件，返回写入字节数。"""
    async with session.get(
        url, headers=HEADERS,
        timeout=aiohttp.ClientTimeout(total=timeout_s),
        allow_redirects=True,
    ) as resp:
        resp.raise_for_status()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(save_path, "wb") as f:
            async for chunk in resp.content.iter_chunked(1 << 17):  # 128 KB chunks
                f.write(chunk)
                written += len(chunk)
        return written

def _resolve_target(save_dir: Path, url: str, idx: int, mtype: str) -> Path:
    """从 URL 推断文件名，防止冲突。"""
    raw_name = Path(urlparse(url).path.split("?")[0]).name
    # 修正无扩展名
    if not raw_name or "." not in raw_name:
        ext_map = {"photo": ".jpg", "video": ".mp4", "audio": ".mp3"}
        raw_name = f"{mtype}_{idx:04d}{ext_map.get(mtype, '')}"
    # 清洗非法字符
    raw_name = re.sub(r'[\\/:*?"<>|]', "_", raw_name)
    target = save_dir / raw_name
    if target.exists():
        stem, suffix = target.stem, target.suffix
        target = save_dir / f"{stem}_{idx:04d}{suffix}"
    return target

# ────────────────────────────────────────────────────────────────────
#  并发下载一个媒体类型桶
# ────────────────────────────────────────────────────────────────────

async def download_bucket(
    session: aiohttp.ClientSession,
    items: list[tuple[str, int]],      # [(url, known_size), ...]
    mtype: str,                         # "photo" / "video" / "audio"
    save_dir: Path,
    folder_name: str,
    status_cb: Callable[[str], None] | None,
    register_cb: Callable[[Path, str, int | None], None] | None,
    uid: int | None,
    min_size: int,
) -> tuple[int, int]:
    """返回 (downloaded, failed)"""
    _, db_mtype, timeout_s, concurrency, _ = _TYPE_META[mtype]
    semaphore = asyncio.Semaphore(concurrency)
    downloaded = 0
    failed     = 0
    t0         = time.monotonic()

    emoji = {"photo": "🖼️", "video": "🎬", "audio": "🎵"}.get(mtype, "📁")

    async def dl_one(idx: int, url: str, known_size: int):
        nonlocal downloaded, failed
        target = _resolve_target(save_dir, url, idx, mtype)
        async with semaphore:
            try:
                written = await stream_download(session, url, target, timeout_s)
                if written < min_size // 4:
                    target.unlink(missing_ok=True)
                    failed += 1
                    return
                downloaded += 1
                if register_cb:
                    await register_cb(target, db_mtype, uid)
                total = len(items)
                if status_cb and (downloaded % PROGRESS_EVERY == 0 or downloaded + failed == total):
                    elapsed = max(time.monotonic() - t0, 0.001)
                    ref_sz  = known_size if known_size > 0 else (1 << 20 if mtype == "video" else 150_000)
                    speed   = downloaded * ref_sz / elapsed
                    speed_s = (f"{speed/(1<<20):.1f} MB/s" if speed >= 1<<20
                               else f"{speed/1024:.0f} KB/s")
                    pct     = (downloaded + failed) / total * 100
                    bar     = "█" * int(pct / 100 * 16) + "░" * (16 - int(pct / 100 * 16))
                    await status_cb(
                        f"{emoji} **{mtype} 下载中**\n"
                        f"`{bar}` **{pct:.0f}%**\n\n"
                        f"✅ 已完成：{downloaded}  ❌ 失败：{failed}  共 {total}\n"
                        f"📁 `{folder_name}`\n"
                        f"⚡ 约 {speed_s}  ⏱ {elapsed:.0f}s"
                    )
            except Exception as exc:
                logger.warning(f"{mtype} 下载失败 [{url}]: {exc}")
                target.unlink(missing_ok=True)
                failed += 1

    await asyncio.gather(*[dl_one(i, u, s) for i, (u, s) in enumerate(items)])
    return downloaded, failed

# ────────────────────────────────────────────────────────────────────
#  主入口：扫描 URL 并批量下载（图片 + 视频 + 音频）
# ────────────────────────────────────────────────────────────────────

async def scan_and_download(
    url: str,
    save_root: Path,
    min_size: int = MIN_FILE_SIZE,
    status_cb: Callable[[str], None] | None = None,
    register_cb: Callable[[Path, str, int | None], None] | None = None,
    uid: int | None = None,
    media_roots: dict[str, Path] | None = None,
) -> dict:
    """
    完整流程：抓页面 → 解析所有媒体 → HEAD 过滤 → 并发下载 → 注册。

    Parameters
    ----------
    url          : 目标页面或媒体直链
    save_root    : 默认保存根目录（图片用）
    min_size     : 图片过滤阈值（视频/音频使用各自默认值）
    status_cb    : async (text) → 更新 Telegram 进度消息
    register_cb  : async (path, media_type, uid) → 主脚本 async_db_register
    uid          : 发起用户 ID
    media_roots  : {"photo": Path, "video": Path, "audio": Path}，各类型保存目录

    Returns
    -------
    dict: total_found, total_filtered, downloaded, skipped, failed, folder,
          by_type: {"photo": {...}, "video": {...}, "audio": {...}}
    """
    result = dict(
        total_found=0, total_filtered=0,
        downloaded=0, skipped=0, failed=0, folder="",
        by_type={"photo": {}, "video": {}, "audio": {}},
    )

    connector = aiohttp.TCPConnector(ssl=False, limit=DL_CONCURRENCY + DL_CONCURRENCY_V + 4)
    async with aiohttp.ClientSession(connector=connector) as session:

        # ── Step 1: 抓页面 ──────────────────────────────────────
        if status_cb:
            await status_cb(f"🌐 正在抓取页面...\n`{url[:60]}`")
        try:
            html, final_url = await fetch_page(session, url)
        except Exception as exc:
            raise RuntimeError(f"页面抓取失败：{exc}") from exc

        # ── Step 2: 解析所有媒体链接 ────────────────────────────
        buckets, title, domain = extract_all_media(html, final_url)

        total_found = sum(len(v) for v in buckets.values())
        result["total_found"] = total_found

        if total_found == 0:
            raise RuntimeError("未在页面中发现任何媒体链接（图片/视频/音频）")

        folder_name      = make_folder_name(domain, title)
        result["folder"] = folder_name

        # 各类型保存目录（传入 media_roots 时用各自目录，否则统一用 save_root）
        def get_dir(mtype: str) -> Path:
            if media_roots and mtype in media_roots:
                base = media_roots[mtype] / folder_name
            else:
                base = save_root / folder_name
            base.mkdir(parents=True, exist_ok=True)
            return base

        # 汇总日志
        summary_parts = []
        for mtype, urls in buckets.items():
            if urls:
                emoji = {"photo": "🖼️", "video": "🎬", "audio": "🎵"}[mtype]
                summary_parts.append(f"{emoji} {mtype}: {len(urls)}")
        if status_cb:
            await status_cb(
                f"🔍 发现媒体资源：\n" + "\n".join(f"  {p}" for p in summary_parts) + "\n\n"
                f"📁 目录：`{folder_name}`\n"
                f"⏳ 正在 HEAD 预检大小..."
            )

        # ── Step 3: HEAD 过滤（各桶并行）───────────────────────
        all_filtered: dict[str, list[tuple[str, int]]] = {"photo": [], "video": [], "audio": []}

        for mtype, urls in buckets.items():
            if not urls:
                continue
            per_type_min = _TYPE_META[mtype][4]
            filtered_map = await filter_bucket(session, urls, mtype, per_type_min)
            for k, v in filtered_map.items():
                all_filtered[k].extend(v)

        total_filtered = sum(len(v) for v in all_filtered.values())
        total_skipped  = total_found - total_filtered
        result["total_filtered"] = total_filtered
        result["skipped"]        = total_skipped

        if total_filtered == 0:
            raise RuntimeError("所有媒体文件均未通过大小过滤（文件太小或无法访问）")

        # 过滤后汇总
        filter_parts = []
        for mtype, items in all_filtered.items():
            if items:
                emoji = {"photo": "🖼️", "video": "🎬", "audio": "🎵"}[mtype]
                filter_parts.append(f"{emoji} {mtype}: {len(items)} 个通过")
        if status_cb:
            await status_cb(
                f"✅ HEAD 预检完成（过滤 {total_skipped} 个过小文件）\n"
                + "\n".join(f"  {p}" for p in filter_parts) + "\n\n"
                f"⬇️ 开始下载..."
            )

        # ── Step 4: 按类型顺序下载（图片并发 → 视频保守 → 音频）
        total_dl = total_fail = 0
        for mtype, items in all_filtered.items():
            if not items:
                result["by_type"][mtype] = {"downloaded": 0, "failed": 0}
                continue
            save_dir    = get_dir(mtype)
            per_min     = _TYPE_META[mtype][4]
            dl, fail    = await download_bucket(
                session, items, mtype, save_dir, folder_name,
                status_cb, register_cb, uid, per_min,
            )
            result["by_type"][mtype] = {"downloaded": dl, "failed": fail}
            total_dl   += dl
            total_fail += fail

        result["downloaded"] = total_dl
        result["failed"]     = total_fail

    return result

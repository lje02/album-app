#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def determine_engine(url: str) -> str:
    """根据 URL 特征分配底层下载引擎，未知网站走 generic 兜底"""
    
    # 1. 知名图站与常见社交平台
    gallery_domains = r'(pixiv\.net|twitter\.com|x\.com|danbooru|gelbooru|rule34|yande\.re|kemono\.party|imgur\.com|pinterest\.com|weibo\.com|instagram\.com|telegra\.ph)'
    image_exts = r'\.(jpg|jpeg|png|webp|gif|avif|bmp|heic)($|\?|#)'
    if re.search(gallery_domains, url, re.IGNORECASE) or re.search(image_exts, url, re.IGNORECASE):
        return 'gallery-dl'
        
    # 2. 知名视频平台
    video_domains = r'(youtube\.com|youtu\.be|bilibili\.com|tiktok\.com|douyin\.com|vimeo\.com|pornhub\.com|xvideos\.com|twitch\.tv)'
    video_exts = r'\.(mp4|mkv|webm|avi|mov|m4v|ts)($|\?|#)'
    if re.search(video_domains, url, re.IGNORECASE) or re.search(video_exts, url, re.IGNORECASE):
        return 'yt-dlp'
        
    # 3. 市面上其余普通网站，全部交给混合泛用路由
    return 'generic'


async def run_ytdlp(url: str, save_dir: Path, status_cb=None, raise_error: bool = True) -> list[Path]:
    """异步调度 yt-dlp"""
    save_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "yt-dlp", "--newline", "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", f"{save_dir}/%(title)s_%(id)s.%(ext)s", url
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    downloaded_files = []
    full_log = []
    last_update = time.monotonic()

    while True:
        line = await process.stdout.readline()
        if not line: break
        line_str = line.decode('utf-8', errors='ignore').strip()
        full_log.append(line_str)
        
        if "[download]" in line_str and "%" in line_str:
            now = time.monotonic()
            if status_cb and (now - last_update > 2.0):
                await status_cb(f"🎬 **yt-dlp 提取中**\n`{line_str[:50]}`...")
                last_update = now
        elif "[Merger] Merging formats into" in line_str:
            try: downloaded_files.append(Path(line_str.split('"')[1]))
            except IndexError: pass
        elif "[download] Destination:" in line_str:
            downloaded_files.append(Path(line_str.replace("[download] Destination:", "").strip()))
        elif "has already been downloaded" in line_str:
            try: downloaded_files.append(Path(line_str.replace("[download]", "").split("has already been downloaded")[0].strip()))
            except Exception: pass

    await process.wait()
    
    if not downloaded_files and raise_error:
        errors = [line for line in full_log if "ERROR:" in line]
        err_msg = "\n".join(errors[:3]) if errors else f"状态码 {process.returncode}"
        raise RuntimeError(f"yt-dlp 失败:\n{err_msg}")
        
    return downloaded_files


async def run_gallerydl(url: str, save_dir: Path, status_cb=None) -> list[Path]:
    """异步调度 gallery-dl"""
    save_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["gallery-dl", "--directory", str(save_dir), url]
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    downloaded_files = []
    last_update = time.monotonic()

    while True:
        line = await process.stdout.readline()
        if not line: break
        line_str = line.decode('utf-8', errors='ignore').strip()
        
        if line_str.startswith("#"):
            now = time.monotonic()
            if status_cb and (now - last_update > 2.0):
                await status_cb(f"🖼️ **gallery-dl 抓取中**\n`{line_str}`")
                last_update = now
        elif line_str.startswith("/") or line_str[1:3] == ":\\":
            downloaded_files.append(Path(line_str))

    await process.wait()
    if process.returncode != 0 and not downloaded_files:
        raise RuntimeError(f"gallery-dl 异常退出 (状态码 {process.returncode})")
        
    return downloaded_files


async def run_generic_fallback(url: str, save_dir: Path, status_cb=None) -> list[Path]:
    """兜底泛用爬虫：暴力抓取普通网页中的图片和基础视频"""
    save_dir.mkdir(parents=True, exist_ok=True)
    downloaded_files = []
    
    try:
        async with aiohttp.ClientSession() as session:
            if status_cb: await status_cb(f"🕸️ **启动 BS4 网页嗅探**\n`{url[:50]}`...")
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15) as resp:
                html = await resp.text()
                
        soup = BeautifulSoup(html, "html.parser")
        media_urls = set()
        
        # 提取常规 img 和 video 标签
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.startswith("data:"): 
                media_urls.add(urljoin(url, src))
                
        for vid in soup.find_all("video"):
            src = vid.get("src")
            if src and not src.startswith("data:"): 
                media_urls.add(urljoin(url, src))
                
        # 过滤有效的扩展名
        valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".avi", ".mov")
        targets = [u for u in media_urls if any(u.lower().split("?")[0].endswith(e) for e in valid_exts)]
        
        if not targets:
            return []
            
        if status_cb: await status_cb(f"🕸️ 嗅探到 {len(targets)} 个媒体，开始并发拉取 (过滤图标中)...")
        
        async def download_one(dl_url, index):
            try:
                ext = "." + dl_url.lower().split("?")[0].split(".")[-1]
                if ext not in valid_exts: ext = ".jpg"
                file_name = f"web_generic_{int(time.time())}_{index:03d}{ext}"
                save_path = save_dir / file_name
                
                async with aiohttp.ClientSession() as dl_session:
                    async with dl_session.get(dl_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30) as r:
                        if r.status == 200:
                            content = await r.read()
                            # 过滤小于 50KB 的网站 Logo 和占位图
                            if len(content) > 51200:
                                with open(save_path, "wb") as f:
                                    f.write(content)
                                return save_path
            except Exception:
                pass
            return None
            
        # 并发执行，最多限制提取前 60 个，防止遇到超级大页面炸内存
        tasks = [download_one(u, i) for i, u in enumerate(targets[:60])]
        results = await asyncio.gather(*tasks)
        downloaded_files = [r for r in results if r is not None]
        
    except Exception as e:
        logger.error(f"泛用爬虫异常: {e}")
        
    return downloaded_files


async def smart_download(url: str, media_roots: dict, status_cb=None) -> tuple[str, list[Path]]:
    """全局智能路由分发"""
    engine = determine_engine(url)
    
    if engine == 'gallery-dl':
        save_dir = media_roots.get("photo") / "url_downloads"
        return "gallery-dl", await run_gallerydl(url, save_dir, status_cb)
        
    elif engine == 'yt-dlp':
        save_dir = media_roots.get("video") / "url_downloads"
        return "yt-dlp", await run_ytdlp(url, save_dir, status_cb, raise_error=True)
        
    else:
        # 【混合模式】未知普通网站
        
        # 1. 先尝试用 yt-dlp 嗅探网页里是不是内嵌了视频播放器
        save_dir_v = media_roots.get("video") / "url_downloads"
        files = []
        try:
            files = await run_ytdlp(url, save_dir_v, status_cb, raise_error=False)
        except Exception:
            pass
            
        if files:
            return "yt-dlp (网页内嵌视频嗅探)", files
            
        # 2. 如果没有任何视频，启动 BS4 爬虫提取整个网页的大图片
        save_dir_p = media_roots.get("photo") / "url_downloads"
        files = await run_generic_fallback(url, save_dir_p, status_cb)
        
        return "泛用网页爬虫", files


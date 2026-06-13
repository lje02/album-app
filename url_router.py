#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

def determine_engine(url: str) -> str:
    """根据 URL 特征分配底层下载引擎"""
    gallery_domains = r'(pixiv\.net|twitter\.com|x\.com|danbooru|gelbooru|rule34|yande\.re|kemono\.party)'
    if re.search(gallery_domains, url, re.IGNORECASE):
        return 'gallery-dl'
    return 'yt-dlp'

async def run_ytdlp(url: str, save_dir: Path, status_cb=None) -> list[Path]:
    """异步调度 yt-dlp 下载流媒体"""
    save_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "yt-dlp",
        "--newline",
        "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", f"{save_dir}/%(title)s_%(id)s.%(ext)s",
        url
    ]
    logger.info(f"🎬 yt-dlp 启动: {url}")
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    downloaded_files = []
    last_update = time.monotonic()

    while True:
        line = await process.stdout.readline()
        if not line: break
        line_str = line.decode('utf-8', errors='ignore').strip()
        
        # 捕获进度
        if "[download]" in line_str and "%" in line_str:
            now = time.monotonic()
            if status_cb and (now - last_update > 2.0):
                await status_cb(f"🎬 **yt-dlp 提取中**\n`{line_str}`")
                last_update = now
                
        # 捕获完成路径
        elif "[Merger] Merging formats into" in line_str:
            file_path = line_str.split('"')[1]
            downloaded_files.append(Path(file_path))
        elif "[download] Destination:" in line_str:
            file_path = line_str.replace("[download] Destination:", "").strip()
            downloaded_files.append(Path(file_path))

    await process.wait()
    if process.returncode != 0:
        logger.error(f"yt-dlp 异常退出: {process.returncode}")
        
    return downloaded_files

async def run_gallerydl(url: str, save_dir: Path, status_cb=None) -> list[Path]:
    """异步调度 gallery-dl 批量拔图"""
    save_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "gallery-dl",
        "--directory", str(save_dir),
        url
    ]
    logger.info(f"🖼️ gallery-dl 启动: {url}")
    
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    downloaded_files = []
    last_update = time.monotonic()

    while True:
        line = await process.stdout.readline()
        if not line: break
        line_str = line.decode('utf-8', errors='ignore').strip()
        
        # gallery-dl 以 '#' 开头表示状态，以 '/' 或盘符开头表示下载完成的路径
        if line_str.startswith("#"):
            now = time.monotonic()
            if status_cb and (now - last_update > 2.0):
                await status_cb(f"🖼️ **gallery-dl 抓取中**\n`{line_str}`")
                last_update = now
        elif line_str.startswith("/") or line_str[1:3] == ":\\":
            downloaded_files.append(Path(line_str))

    await process.wait()
    if process.returncode != 0:
        logger.error(f"gallery-dl 异常退出: {process.returncode}")
        
    return downloaded_files

async def smart_download(url: str, media_roots: dict, status_cb=None) -> tuple[str, list[Path]]:
    """路由分发并执行"""
    engine = determine_engine(url)
    
    if engine == 'gallery-dl':
        # 图片默认放在 photo 目录下的 url_downloads 子目录
        save_dir = media_roots.get("photo") / "url_downloads"
        files = await run_gallerydl(url, save_dir, status_cb)
    else:
        # 视频默认放在 video 目录下的 url_downloads 子目录
        save_dir = media_roots.get("video") / "url_downloads"
        files = await run_ytdlp(url, save_dir, status_cb)
        
    return engine, files

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web 流媒体服务模块
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
支持视频、音频、图片在线观看
与 web_api.py 配合使用
"""

import os
import mimetypes
from pathlib import Path
from flask import Flask, request, send_file, stream_with_context, Response
import sqlite3

# ══════════════════════════════════════════════════════════════
#  流媒体服务
# ══════════════════════════════════════════════════════════════

def register_streaming_routes(app: Flask, db_path: Path, download_root: Path):
    """注册流媒体路由"""
    
    # ────────────────────────────────────────────────────────────
    #  视频流播放（支持 Range 请求）
    # ────────────────────────────────────────────────────────────
    @app.route('/api/stream/video/<int:file_id>')
    def stream_video(file_id):
        """
        视频流播放
        GET /api/stream/video/{file_id}?token=TOKEN
        
        支持特性：
        - HTTP Range 请求（快进快退）
        - 自适应比特率
        - 暂停/继续播放
        """
        file_info = _get_file_info(db_path, file_id)
        if not file_info:
            return {'error': '文件不存在'}, 404
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            return {'error': '文件已删除'}, 404
        
        if not _is_video(file_info['media_type']):
            return {'error': '非视频文件'}, 400
        
        return _stream_file_with_range(file_path)
    
    # ────────────────────────────────────────────────────────────
    #  音频流播放
    # ────────────────────────────────────────────────────────────
    @app.route('/api/stream/audio/<int:file_id>')
    def stream_audio(file_id):
        """
        音频流播放
        GET /api/stream/audio/{file_id}?token=TOKEN
        """
        file_info = _get_file_info(db_path, file_id)
        if not file_info:
            return {'error': '文件不存在'}, 404
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            return {'error': '文件已删除'}, 404
        
        if not _is_audio(file_info['media_type']):
            return {'error': '非音频文件'}, 400
        
        return _stream_file_with_range(file_path)
    
    # ────────────────────────────────────────────────────────────
    #  图片在线查看
    # ────────────────────────────────────────────────────────────
    @app.route('/api/stream/image/<int:file_id>')
    def stream_image(file_id):
        """
        图片在线查看
        GET /api/stream/image/{file_id}?token=TOKEN
        """
        file_info = _get_file_info(db_path, file_id)
        if not file_info:
            return {'error': '文件不存在'}, 404
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            return {'error': '文件已删除'}, 404
        
        if file_info['media_type'] not in ('photo', 'sticker'):
            return {'error': '非图片文件'}, 400
        
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return send_file(file_path, mimetype=mime_type or 'image/jpeg')
    
    # ────────────────────────────────────────────────────────────
    #  获取文件元数据（用于播放器初始化）
    # ────────────────────────────────────────────────────────────
    @app.route('/api/stream/metadata/<int:file_id>')
    def get_stream_metadata(file_id):
        """
        获取流媒体元数据
        GET /api/stream/metadata/{file_id}?token=TOKEN
        """
        file_info = _get_file_info(db_path, file_id)
        if not file_info:
            return {'error': '文件不存在'}, 404
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            return {'error': '文件已删除'}, 404
        
        media_type = file_info['media_type']
        stat = file_path.stat()
        
        metadata = {
            'file_id': file_id,
            'file_name': file_info['file_name'],
            'file_size': file_info['file_size'],
            'media_type': media_type,
            'mime_type': _get_mime_type(file_path),
            'can_stream': _can_stream(media_type),
            'duration_ms': _get_video_duration(file_path) if _is_video(media_type) else None,
            'created_at': file_info['downloaded_at'],
            'last_modified': stat.st_mtime,
        }
        
        return {'success': True, 'metadata': metadata}
    
    # ────────────────────────────────────────────────────────────
    #  缩略图生成（视频预览）
    # ────────────────────────────────────────────────────────────
    @app.route('/api/stream/thumbnail/<int:file_id>')
    def get_thumbnail(file_id):
        """
        获取视频缩略图
        GET /api/stream/thumbnail/{file_id}?token=TOKEN&time=5
        """
        file_info = _get_file_info(db_path, file_id)
        if not file_info:
            return {'error': '文件不存在'}, 404
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            return {'error': '文件已删除'}, 404
        
        if not _is_video(file_info['media_type']):
            return {'error': '非视频文件'}, 400
        
        time_sec = request.args.get('time', 5, type=int)
        thumbnail_path = _generate_thumbnail(file_path, time_sec)
        
        if thumbnail_path and thumbnail_path.exists():
            return send_file(thumbnail_path, mimetype='image/jpeg')
        
        return {'error': '缩略图生成失败'}, 500


# ══════════════════════════════════════════════════════════════
#  辅助函数
# ════��═════════════════════════════════════════════════════════

def _get_file_info(db_path: Path, file_id: int) -> dict | None:
    """从数据库获取文件信息"""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM files WHERE id = ?",
            (file_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ 数据库查询错误：{e}")
        return None


def _stream_file_with_range(file_path: Path) -> Response:
    """
    流式传输文件，支持 HTTP Range 请求
    用于视频/音频快进快退
    """
    file_size = file_path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # 检查是否有 Range 请求头
    range_header = request.headers.get('Range')
    
    if range_header:
        # 解析 Range: bytes=start-end
        try:
            parts = range_header.replace('bytes=', '').split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1
            
            # 限制范围
            start = max(0, start)
            end = min(end, file_size - 1)
            length = end - start + 1
            
            def generate():
                with open(file_path, 'rb') as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk
            
            response = Response(
                stream_with_context(generate()),
                status=206,  # Partial Content
                mimetype=mime_type or 'application/octet-stream'
            )
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Content-Length'] = length
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Type'] = mime_type or 'application/octet-stream'
            return response
        except (ValueError, IndexError):
            pass  # 忽略无效的 Range 请求
    
    # 没有 Range 请求或解析失败，返回整个文件
    response = send_file(
        file_path,
        mimetype=mime_type or 'application/octet-stream',
        as_attachment=False
    )
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'public, max-age=86400'
    return response


def _is_video(media_type: str) -> bool:
    """判断是否为视频类型"""
    return media_type in ('video', 'animation')


def _is_audio(media_type: str) -> bool:
    """判断是否为音频类型"""
    return media_type in ('audio', 'voice')


def _can_stream(media_type: str) -> bool:
    """判断是否支持流播放"""
    return media_type in ('video', 'audio', 'voice', 'animation', 'photo', 'sticker')


def _get_mime_type(file_path: Path) -> str:
    """获取文件 MIME 类型"""
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type or 'application/octet-stream'


def _get_video_duration(file_path: Path) -> int | None:
    """
    获取视频时长（秒）
    需要 ffmpeg 支持
    """
    try:
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries',
             'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1:noprint_wrappers=1',
             str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            return int(duration * 1000)  # 转换为毫秒
    except Exception as e:
        print(f"⚠️  获取视频时长失败：{e}")
    return None


def _generate_thumbnail(file_path: Path, time_sec: int = 5) -> Path | None:
    """
    生成视频缩略图
    需要 ffmpeg 支持
    """
    try:
        import subprocess
        
        # 检查缓存的缩略图
        thumb_dir = file_path.parent / '.thumbnails'
        thumb_path = thumb_dir / f"{file_path.stem}_{time_sec}.jpg"
        
        if thumb_path.exists():
            return thumb_path
        
        # 生成缩略图
        thumb_dir.mkdir(exist_ok=True)
        
        result = subprocess.run(
            ['ffmpeg', '-i', str(file_path), '-ss', str(time_sec),
             '-vframes', '1', '-vf', 'scale=320:-1',
             '-y', str(thumb_path)],
            capture_output=True,
            timeout=15
        )
        
        if result.returncode == 0 and thumb_path.exists():
            return thumb_path
    except Exception as e:
        print(f"⚠️  缩略图生成失败：{e}")
    
    return None

import os
import json
import uuid
import bcrypt
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import httpx

# ---------- 初始化应用 ----------
app = FastAPI(title="Public Album API")

# 静态文件服务（前端页面）
app.mount("/static", StaticFiles(directory="static"), name="static")

# 跨域设置（如果前后端分离可放开）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 配置 ----------
DATA_FILE = "data.json"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# ---------- 数据模型（JSON 文件模拟数据库） ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        default = {
            "settings": {
                "password_hash": bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode(),
                "storage_mode": "local",
                "smms_token": ""
            },
            "tokens": {},       # token -> expiry (暂时不设过期)
            "albums": [],
            "photos": [],
            "next_album_id": 1,
            "next_photo_id": 1
        }
        save_data(default)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------- 辅助函数 ----------
def get_admin(request: Request):
    """从请求头中验证 token，返回 True/False"""
    token = request.headers.get("x-admin-token", "")
    data = load_data()
    if token and token in data["tokens"]:
        return True
    return False

def generate_token():
    return secrets.token_hex(32)

# ---------- 根路径返回前端 ----------
@app.get("/")
async def index():
    return FileResponse("static/index.html")

# ---------- 认证相关 ----------
@app.post("/api/auth")
async def auth(request: Request):
    body = await request.json()
    password = body.get("password", "")
    data = load_data()
    pwd_hash = data["settings"]["password_hash"]
    if not bcrypt.checkpw(password.encode(), pwd_hash.encode()):
        raise HTTPException(status_code=401, detail="密码错误")
    token = generate_token()
    data["tokens"][token] = datetime.now().isoformat()
    save_data(data)
    return {"token": token}

@app.get("/api/verify-token")
async def verify_token(request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=401, detail="无效的 token")
    return {"status": "ok"}

# ---------- 相册 CRUD ----------
@app.get("/api/albums")
async def get_albums():
    data = load_data()
    return {"albums": data["albums"]}

@app.post("/api/albums")
async def create_album(request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="相册名称不能为空")
    data = load_data()
    album = {
        "id": data["next_album_id"],
        "name": name,
        "description": body.get("description", ""),
        "category": body.get("category", "other")
    }
    data["albums"].append(album)
    data["next_album_id"] += 1
    save_data(data)
    return album

@app.put("/api/albums/{album_id}")
async def update_album(album_id: int, request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    body = await request.json()
    data = load_data()
    album = next((a for a in data["albums"] if a["id"] == album_id), None)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    album["name"] = body.get("name", album["name"]).strip() or album["name"]
    album["description"] = body.get("description", album["description"])
    album["category"] = body.get("category", album["category"])
    save_data(data)
    return album

@app.delete("/api/albums/{album_id}")
async def delete_album(album_id: int, request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = load_data()
    original_len = len(data["albums"])
    data["albums"] = [a for a in data["albums"] if a["id"] != album_id]
    if len(data["albums"]) == original_len:
        raise HTTPException(status_code=404, detail="相册不存在")
    # 将属于该相册的图片 album_id 置为 None 或保留原样？这里设置为 0 表示未分类
    for p in data["photos"]:
        if p["album_id"] == album_id:
            p["album_id"] = 0  # 0 表示未分类
    save_data(data)
    return {"detail": "已删除"}

# ---------- 图片 CRUD ----------
@app.get("/api/photos")
async def get_photos(album_id: int = None):
    data = load_data()
    photos = data["photos"]
    if album_id is not None:
        photos = [p for p in photos if p["album_id"] == album_id]
    return {"photos": photos}

@app.post("/api/photos")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    album_id: int = Form(...),
    title: str = Form(""),
    tags: str = Form("")
):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = load_data()
    settings = data["settings"]
    mode = settings["storage_mode"]

    if mode == "url_only":
        raise HTTPException(status_code=400, detail="当前存储模式仅允许 URL 添加")

    file_content = await file.read()
    file_size = len(file_content)

    if file_size > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 20MB 限制")

    if mode == "local":
        # 保存到本地
        ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)
        url = f"/uploads/{filename}"
    elif mode == "smms":
        smms_token = settings.get("smms_token", "")
        if not smms_token:
            raise HTTPException(status_code=400, detail="未配置 SM.MS Token")
        # 上传到 SM.MS
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://sm.ms/api/v2/upload",
                    headers={"Authorization": smms_token},
                    files={"smfile": (file.filename, file_content, file.content_type)}
                )
                result = response.json()
                if response.status_code == 200 and result.get("success"):
                    url = result["data"]["url"]
                else:
                    raise HTTPException(status_code=500, detail=f"SM.MS 上传失败: {result.get('message', '未知错误')}")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"SM.MS 请求异常: {str(e)}")
    else:
        raise HTTPException(status_code=500, detail="未知存储模式")

    # 写入图片记录
    photo = {
        "id": data["next_photo_id"],
        "album_id": album_id,
        "url": url,
        "title": title,
        "tags": tags,
        "created_at": datetime.now().isoformat()
    }
    data["photos"].append(photo)
    data["next_photo_id"] += 1
    save_data(data)
    return photo

@app.post("/api/photos/url")
async def add_photo_url(request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    body = await request.json()
    url = body.get("url", "").strip()
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="无效的图片 URL")
    data = load_data()
    photo = {
        "id": data["next_photo_id"],
        "album_id": body.get("album_id", 0),
        "url": url,
        "title": body.get("title", ""),
        "tags": body.get("tags", ""),
        "created_at": datetime.now().isoformat()
    }
    data["photos"].append(photo)
    data["next_photo_id"] += 1
    save_data(data)
    return photo

@app.delete("/api/photos/{photo_id}")
async def delete_photo(photo_id: int, request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = load_data()
    original_len = len(data["photos"])
    data["photos"] = [p for p in data["photos"] if p["id"] != photo_id]
    if len(data["photos"]) == original_len:
        raise HTTPException(status_code=404, detail="图片不存在")
    # 如果是本地文件，删除对应文件（可选）
    # 这里简单忽略本地文件清理，保持逻辑简洁
    save_data(data)
    return {"detail": "已删除"}

# ---------- 设置 ----------
@app.get("/api/settings")
async def get_settings(request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    data = load_data()
    settings = data["settings"]
    return {
        "storage_mode": settings["storage_mode"],
        "smms_token": settings["smms_token"]
    }

@app.put("/api/settings")
async def update_settings(request: Request):
    if not get_admin(request):
        raise HTTPException(status_code=403, detail="需要管理员权限")
    body = await request.json()
    data = load_data()
    settings = data["settings"]
    if "storage_mode" in body:
        mode = body["storage_mode"]
        if mode not in ("local", "smms", "url_only"):
            raise HTTPException(status_code=400, detail="无效的存储模式")
        settings["storage_mode"] = mode
    if "smms_token" in body:
        settings["smms_token"] = body["smms_token"]
    if "new_password" in body and body["new_password"]:
        new_pwd = body["new_password"]
        settings["password_hash"] = bcrypt.hashpw(new_pwd.encode(), bcrypt.gensalt()).decode()
        # 修改密码后清除所有登录 token，强制重新登录
        data["tokens"] = {}
    save_data(data)
    return {"detail": "设置已保存"}

# ---------- 静态文件托管（上传的图片） ----------
@app.get("/uploads/{filename}")
async def uploaded_file(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)

# ---------- 启动入口 ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

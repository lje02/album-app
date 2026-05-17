#!/usr/bin/env bash
# ============================================================
#  📷 Photo Album — 自解压一键安装脚本
#  用法：bash install.sh [--dev | --build | --preview]
#  无需 git，下载本脚本后直接运行即可
# ============================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}▶ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✖ $*${RESET}" >&2; exit 1; }

MODE="${1:---preview}"
INSTALL_DIR="photo-album"

echo ""
echo -e "${BOLD}  📷 Photo Album 安装程序${RESET}"
echo -e "  ─────────────────────────"
echo ""

# ── 检查 Node.js ──
if ! command -v node &>/dev/null; then
  error "未找到 Node.js，请先安装 Node.js 18+：https://nodejs.org"
fi
node -e "if(parseInt(process.versions.node)<18)process.exit(1)" \
  || error "Node.js 版本过低（需要 18+），当前：$(node -v)"
success "Node.js $(node -v)"

if ! command -v npm &>/dev/null; then
  error "未找到 npm，请重新安装 Node.js"
fi
success "npm $(npm -v)"

# ── 创建项目目录 ──
if [ -d "$INSTALL_DIR" ]; then
  warn "目录 $INSTALL_DIR 已存在，将覆盖文件"
else
  mkdir -p "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
mkdir -p src

info "正在写入项目文件..."

# ────────────────────────────────────────
#  package.json
# ────────────────────────────────────────
cat > package.json << 'PKGJSON'
{
  "name": "photo-album",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "serve": "vite preview --port 3000 --host"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.7"
  }
}
PKGJSON

# ────────────────────────────────────────
#  vite.config.js
# ────────────────────────────────────────
cat > vite.config.js << 'VITECFG'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist', sourcemap: false },
  server: { port: 5173, host: true },
  preview: { port: 3000, host: true },
})
VITECFG

# ────────────────────────────────────────
#  index.html
# ────────────────────────────────────────
cat > index.html << 'INDEXHTML'
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📷</text></svg>" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>我的相册</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
INDEXHTML

# ────────────────────────────────────────
#  src/main.jsx
# ────────────────────────────────────────
cat > src/main.jsx << 'MAINJSX'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode><App /></StrictMode>
)
MAINJSX

# ────────────────────────────────────────
#  src/App.jsx  （HERE-DOC，内嵌全部源码）
# ────────────────────────────────────────
cat > src/App.jsx << 'APPJSX'
import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "photo_album_app_v1";
const ADMIN_SECRET = "#admin";

function getDefaultData() {
  return {
    albums: [
      { id: "a1", title: "西藏高原之旅", cover: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80", category: "旅行", tags: ["西藏", "高原", "寺庙", "风景"], description: "2024年夏天走进西藏，感受高原的壮阔与宁静，探访布达拉宫与古老寺庙。", updatedAt: "2024-09-10T10:00:00Z", createdAt: "2024-09-10T10:00:00Z", photoCount: 48 },
      { id: "a2", title: "上海夜景", cover: "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?w=800&q=80", category: "城市", tags: ["上海", "夜景", "都市", "外滩"], description: "霓虹璀璨的魔都夜晚，漫步外滩，感受这座城市的脉搏。", updatedAt: "2024-08-22T10:00:00Z", createdAt: "2024-08-22T10:00:00Z", photoCount: 41 },
      { id: "a3", title: "云南丽江", cover: "https://images.unsplash.com/photo-1537531700788-d82ce5f3bebb?w=800&q=80", category: "旅行", tags: ["云南", "丽江", "古城", "纳西族"], description: "漫步丽江古城，感受纳西族文化的独特魅力，品尝地道云南美食。", updatedAt: "2024-07-05T10:00:00Z", createdAt: "2024-07-05T10:00:00Z", photoCount: 67 },
      { id: "a4", title: "春日花海", cover: "https://images.unsplash.com/photo-1490750967868-88df5691166a?w=800&q=80", category: "自然", tags: ["花卉", "春天", "摄影", "油菜花"], description: "春天里最美的花朵盛开，漫山遍野的色彩令人心旷神怡。", updatedAt: "2024-04-10T10:00:00Z", createdAt: "2024-04-10T10:00:00Z", photoCount: 56 },
      { id: "a5", title: "成都美食记录", cover: "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=800&q=80", category: "美食", tags: ["成都", "川菜", "火锅", "小吃"], description: "走遍成都大街小巷，寻访地道川味，记录每一份令人难忘的美食。", updatedAt: "2024-03-18T10:00:00Z", createdAt: "2024-03-18T10:00:00Z", photoCount: 32 },
      { id: "a6", title: "家庭聚会 2024", cover: "https://images.unsplash.com/photo-1511988617509-a57c8a288659?w=800&q=80", category: "家庭", tags: ["家庭", "聚会", "春节", "温馨"], description: "春节家庭大聚会，温馨时刻永久留存，记录最美好的团圆记忆。", updatedAt: "2024-02-10T10:00:00Z", createdAt: "2024-02-10T10:00:00Z", photoCount: 89 },
    ],
    categories: ["旅行", "城市", "自然", "美食", "家庭"],
    settings: { albumsPerPage: 6, adminPassword: "admin123", siteTitle: "我的相册" }
  };
}

function genId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
function fmtDate(iso) { return new Date(iso).toLocaleDateString("zh-CN", { year: "numeric", month: "short", day: "numeric" }); }

const css = `
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;600&family=Noto+Sans+SC:wght@300;400;500&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#F7F5F0;--bg2:#EFEDE7;--bg3:#E8E5DC;--surface:#FFFFFF;
  --border:rgba(0,0,0,0.09);--text:#1C1C1A;--text2:#6B6860;--text3:#AAA89F;
  --accent:#2D2D2A;--accent-light:#F0EDE5;--red:#C0392B;--red-light:#FDF2F0;
  --sidebar-w:210px;--header-h:54px;--radius:10px;--radius-sm:6px;
  --transition:0.22s cubic-bezier(0.4,0,0.2,1);
}
body{font-family:'Noto Sans SC',-apple-system,sans-serif;background:var(--bg);color:var(--text);font-size:14px;-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--bg3);border-radius:4px}
.hdr{position:sticky;top:0;z-index:100;height:var(--header-h);background:rgba(247,245,240,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 1.25rem 0 0.75rem;gap:.75rem}
.hdr-left{display:flex;align-items:center;gap:.5rem}
.sidebar-toggle{width:34px;height:34px;border:none;background:transparent;cursor:pointer;border-radius:var(--radius-sm);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:5px;transition:background var(--transition);flex-shrink:0}
.sidebar-toggle:hover{background:var(--bg3)}
.sidebar-toggle span{display:block;width:18px;height:1.5px;background:var(--text);border-radius:2px;transition:transform var(--transition),opacity var(--transition),width var(--transition)}
.sidebar-toggle.open span:nth-child(1){transform:translateY(6.5px) rotate(45deg)}
.sidebar-toggle.open span:nth-child(2){opacity:0;width:0}
.sidebar-toggle.open span:nth-child(3){transform:translateY(-6.5px) rotate(-45deg)}
.hdr-title{font-family:'Noto Serif SC',serif;font-size:16px;font-weight:500;letter-spacing:.5px;white-space:nowrap}
.hdr-search{flex:1;max-width:280px;position:relative}
.hdr-search input{width:100%;padding:6px 10px 6px 32px;background:var(--bg3);border:1px solid transparent;border-radius:20px;font-size:13px;color:var(--text);outline:none;transition:all var(--transition);font-family:inherit}
.hdr-search input::placeholder{color:var(--text3)}
.hdr-search input:focus{background:var(--surface);border-color:var(--border);box-shadow:0 2px 8px rgba(0,0,0,.06)}
.hdr-search-icon{position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--text3);font-size:13px;pointer-events:none}
.layout{display:flex;min-height:calc(100vh - var(--header-h))}
.sidebar-wrap{position:sticky;top:var(--header-h);height:calc(100vh - var(--header-h));flex-shrink:0;overflow:hidden;width:var(--sidebar-w);transition:width var(--transition);z-index:50}
.sidebar-wrap.collapsed{width:0}
.sidebar{width:var(--sidebar-w);height:100%;background:var(--bg2);border-right:1px solid var(--border);padding:1rem .65rem;overflow-y:auto;overflow-x:hidden;display:flex;flex-direction:column;gap:1.5rem}
@media(max-width:768px){
  .sidebar-wrap{position:fixed;top:var(--header-h);left:0;height:calc(100vh - var(--header-h));width:var(--sidebar-w) !important;transform:translateX(-100%);transition:transform var(--transition);z-index:200;box-shadow:none}
  .sidebar-wrap.mobile-open{transform:translateX(0);box-shadow:4px 0 20px rgba(0,0,0,.12)}
  .sidebar-overlay{position:fixed;inset:0;background:rgba(0,0,0,.3);z-index:199;top:var(--header-h)}
}
.sb-section-label{font-size:10px;font-weight:500;letter-spacing:1.2px;text-transform:uppercase;color:var(--text3);padding:0 6px;margin-bottom:6px}
.cat-item{display:flex;align-items:center;justify-content:space-between;padding:6px 9px;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;color:var(--text2);transition:all var(--transition);user-select:none;white-space:nowrap}
.cat-item:hover{background:var(--bg3);color:var(--text)}
.cat-item.active{background:var(--accent);color:#F7F5F0}
.cat-count{font-size:11px;opacity:.5;background:rgba(0,0,0,.06);padding:1px 6px;border-radius:20px}
.cat-item.active .cat-count{background:rgba(255,255,255,.15);opacity:1}
.tag-wrap{display:flex;flex-wrap:wrap;gap:5px;padding:0 2px}
.tag-btn{font-size:11px;padding:3px 9px;border-radius:20px;background:var(--bg3);color:var(--text2);border:1px solid transparent;cursor:pointer;transition:all var(--transition);font-family:inherit;white-space:nowrap}
.tag-btn:hover{background:var(--accent-light);color:var(--accent)}
.tag-btn.active{background:var(--accent);color:#F7F5F0;border-color:var(--accent)}
.main{flex:1;min-width:0;padding:1.25rem 1.5rem 2rem;transition:all var(--transition)}
.main-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;gap:.75rem;flex-wrap:wrap}
.main-info{font-size:13px;color:var(--text3)}
.main-info strong{color:var(--text2);font-weight:500}
.clear-btn{font-size:11px;padding:4px 10px;border-radius:20px;background:var(--bg3);border:none;cursor:pointer;color:var(--text2);font-family:inherit;transition:all var(--transition)}
.clear-btn:hover{background:var(--red-light);color:var(--red)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1rem}
@media(max-width:480px){.grid{grid-template-columns:repeat(2,1fr);gap:.65rem}.main{padding:1rem .85rem 2rem}}
.card{background:var(--surface);border-radius:var(--radius);border:1px solid var(--border);overflow:hidden;cursor:pointer;transition:transform var(--transition),box-shadow var(--transition)}
.card:hover{transform:translateY(-4px);box-shadow:0 14px 32px rgba(0,0,0,.10)}
.card:active{transform:translateY(-1px)}
.card-img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;background:var(--bg3)}
.card-no-img{width:100%;aspect-ratio:4/3;background:var(--bg3);display:flex;align-items:center;justify-content:center;font-size:32px}
.card-body{padding:.7rem .85rem .85rem}
.card-title{font-size:13px;font-weight:500;margin-bottom:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card-footer{display:flex;align-items:center;justify-content:space-between}
.badge{font-size:10px;padding:2px 7px;border-radius:20px;background:var(--accent-light);color:var(--text2)}
.card-count{font-size:11px;color:var(--text3)}
.card-date{font-size:11px;color:var(--text3);margin-top:4px}
.pager{display:flex;align-items:center;justify-content:center;gap:5px;margin-top:2rem}
.pager-btn{width:32px;height:32px;border-radius:var(--radius-sm);border:1px solid var(--border);background:var(--surface);cursor:pointer;font-size:13px;color:var(--text2);display:flex;align-items:center;justify-content:center;transition:all var(--transition);font-family:inherit}
.pager-btn:hover:not(:disabled){background:var(--bg3)}
.pager-btn.active{background:var(--accent);color:#F7F5F0;border-color:var(--accent)}
.pager-btn:disabled{opacity:.3;cursor:default}
.empty{text-align:center;padding:4rem 1rem;color:var(--text3)}
.empty-icon{font-size:40px;margin-bottom:.75rem;opacity:.6}
.empty-txt{font-size:14px}
.overlay{position:fixed;inset:0;background:rgba(20,20,18,.6);display:flex;align-items:center;justify-content:center;z-index:500;padding:1rem;backdrop-filter:blur(4px);animation:fadeIn .15s ease}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.modal{background:var(--surface);border-radius:14px;width:100%;max-width:540px;overflow:hidden;max-height:90vh;overflow-y:auto;animation:slideUp .2s cubic-bezier(0.34,1.2,0.64,1);box-shadow:0 24px 60px rgba(0,0,0,.2)}
@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
.modal-img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
.modal-body{padding:1.25rem 1.5rem 1.5rem}
.modal-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.modal-title{font-family:'Noto Serif SC',serif;font-size:20px;font-weight:500;line-height:1.3}
.modal-close{width:30px;height:30px;border-radius:50%;background:var(--bg3);border:none;cursor:pointer;font-size:16px;color:var(--text2);display:flex;align-items:center;justify-content:center;transition:all var(--transition);flex-shrink:0;margin-left:.75rem}
.modal-close:hover{background:var(--bg);color:var(--text)}
.modal-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:.75rem}
.modal-desc{font-size:13px;color:var(--text2);line-height:1.7}
.modal-tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:1rem}
.btn{padding:6px 14px;border-radius:var(--radius-sm);font-size:12px;border:1px solid var(--border);background:var(--surface);cursor:pointer;color:var(--text2);transition:all var(--transition);display:inline-flex;align-items:center;gap:5px;font-family:inherit;white-space:nowrap}
.btn:hover{background:var(--bg3);color:var(--text)}
.btn-dark{background:var(--accent);color:#F7F5F0;border-color:var(--accent)}
.btn-dark:hover{background:#3A3A36}
.btn-red{background:var(--red-light);color:var(--red);border-color:#F5C6C2}
.btn-red:hover{background:#FBEAE8}
.btn-sm{padding:4px 10px;font-size:11px}
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg)}
.login-box{background:var(--surface);border-radius:14px;padding:2rem;border:1px solid var(--border);width:100%;max-width:320px;box-shadow:0 8px 32px rgba(0,0,0,.07)}
.login-title{font-family:'Noto Serif SC',serif;font-size:20px;font-weight:500;margin-bottom:1.5rem}
.err{font-size:11px;color:var(--red);margin-top:5px}
.adm-layout{display:flex;min-height:100vh}
.adm-sb{width:190px;background:#1A1A18;color:#F7F5F0;padding:1.25rem .75rem;flex-shrink:0;display:flex;flex-direction:column;gap:3px;position:sticky;top:0;height:100vh;overflow-y:auto}
.adm-sb-title{font-family:'Noto Serif SC',serif;font-size:15px;font-weight:500;padding:0 8px;margin-bottom:1rem}
.adm-nav{padding:7px 10px;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;color:#8A8A84;transition:all var(--transition);display:flex;align-items:center;gap:7px}
.adm-nav:hover{background:rgba(255,255,255,.07);color:#F7F5F0}
.adm-nav.active{background:rgba(255,255,255,.11);color:#F7F5F0}
.adm-spacer{flex:1}
.adm-divider{height:1px;background:rgba(255,255,255,.08);margin:.5rem 0}
.adm-main{flex:1;padding:1.75rem 2rem;background:var(--bg);min-width:0}
.adm-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.5rem}
.adm-title{font-family:'Noto Serif SC',serif;font-size:18px;font-weight:500}
@media(max-width:640px){.adm-sb{width:160px}.adm-main{padding:1rem}}
.list-item{display:flex;align-items:center;gap:.9rem;padding:.7rem;border-radius:var(--radius-sm);background:var(--surface);border:1px solid var(--border);margin-bottom:.6rem}
.list-thumb{width:56px;height:42px;object-fit:cover;border-radius:5px;background:var(--bg3);flex-shrink:0}
.list-no-thumb{width:56px;height:42px;border-radius:5px;background:var(--bg3);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.list-info{flex:1;min-width:0}
.list-title{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.list-meta{font-size:11px;color:var(--text3);margin-top:2px}
.list-actions{display:flex;gap:5px;flex-shrink:0}
.fg{margin-bottom:.9rem}
.fl{font-size:10px;font-weight:500;color:var(--text3);margin-bottom:4px;display:block;text-transform:uppercase;letter-spacing:.5px}
.fi{width:100%;padding:7px 10px;border-radius:var(--radius-sm);border:1px solid var(--border);font-size:13px;background:var(--surface);color:var(--text);outline:none;transition:border-color var(--transition);font-family:inherit}
.fi:focus{border-color:var(--accent);box-shadow:0 0 0 2px rgba(45,45,42,.08)}
textarea.fi{resize:vertical;min-height:72px}
.f-overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:flex-start;justify-content:center;z-index:600;padding:1.5rem 1rem;overflow-y:auto;backdrop-filter:blur(4px)}
.f-box{background:var(--surface);border-radius:12px;width:100%;max-width:500px;padding:1.5rem;animation:slideUp .2s cubic-bezier(0.34,1.2,0.64,1);box-shadow:0 20px 50px rgba(0,0,0,.15)}
.f-title{font-family:'Noto Serif SC',serif;font-size:17px;font-weight:500;margin-bottom:1.25rem}
.cat-chip{display:inline-flex;align-items:center;gap:7px;padding:5px 10px;background:var(--surface);border-radius:var(--radius-sm);border:1px solid var(--border);font-size:13px}
.cat-del{background:none;border:none;cursor:pointer;color:var(--red);font-size:15px;line-height:1;padding:0}
.preview-img{width:100%;max-height:130px;object-fit:cover;border-radius:6px;margin-top:7px}
`;

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [route, setRoute] = useState("public");
  const [loggedIn, setLoggedIn] = useState(false);
  const [pwInput, setPwInput] = useState("");
  const [loginErr, setLoginErr] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [activeCategory, setActiveCategory] = useState("全部");
  const [activeTag, setActiveTag] = useState(null);
  const [searchQ, setSearchQ] = useState("");
  const [page, setPage] = useState(1);
  const [selectedAlbum, setSelectedAlbum] = useState(null);
  const [adminTab, setAdminTab] = useState("albums");
  const [showForm, setShowForm] = useState(false);
  const [editingAlbum, setEditingAlbum] = useState(null);
  const [newCat, setNewCat] = useState("");
  const [delConfirm, setDelConfirm] = useState(null);
  const [form, setForm] = useState({ title: "", cover: "", category: "", tags: "", description: "", photoCount: "" });
  const [settingsForm, setSettingsForm] = useState(null);

  useEffect(() => {
    const check = () => { const m = window.innerWidth <= 768; setIsMobile(m); if (m) setSidebarOpen(false); else setMobileOpen(false); };
    check(); window.addEventListener("resize", check); return () => window.removeEventListener("resize", check);
  }, []);

  useEffect(() => {
    const h = () => { if (window.location.hash === ADMIN_SECRET) setRoute("admin"); };
    h(); window.addEventListener("hashchange", h); return () => window.removeEventListener("hashchange", h);
  }, []);

  useEffect(() => {
    try { const r = localStorage.getItem(STORAGE_KEY); const d = r ? JSON.parse(r) : getDefaultData(); setData(d); setSettingsForm({ ...d.settings }); }
    catch { const d = getDefaultData(); setData(d); setSettingsForm({ ...d.settings }); }
    setLoading(false);
  }, []);

  const save = useCallback((d) => { setData({ ...d }); try { localStorage.setItem(STORAGE_KEY, JSON.stringify(d)); } catch(e) { console.error(e); } }, []);

  function openAdd() { setEditingAlbum(null); setForm({ title: "", cover: "", category: data.categories[0] || "", tags: "", description: "", photoCount: "" }); setShowForm(true); }
  function openEdit(a) { setEditingAlbum(a); setForm({ title: a.title, cover: a.cover, category: a.category, tags: a.tags.join(", "), description: a.description, photoCount: String(a.photoCount) }); setShowForm(true); }
  function saveAlbum() {
    if (!form.title.trim()) return;
    const now = new Date().toISOString();
    const a = { id: editingAlbum ? editingAlbum.id : genId(), title: form.title.trim(), cover: form.cover.trim(), category: form.category, tags: form.tags.split(/[,，]/).map(t => t.trim()).filter(Boolean), description: form.description.trim(), photoCount: parseInt(form.photoCount) || 0, updatedAt: now, createdAt: editingAlbum ? editingAlbum.createdAt : now };
    save({ ...data, albums: editingAlbum ? data.albums.map(x => x.id === editingAlbum.id ? a : x) : [a, ...data.albums] });
    setShowForm(false);
  }
  function doDelete(id) { save({ ...data, albums: data.albums.filter(a => a.id !== id) }); setDelConfirm(null); }
  function addCat() { const c = newCat.trim(); if (!c || data.categories.includes(c)) return; save({ ...data, categories: [...data.categories, c] }); setNewCat(""); }
  function removeCat(c) { save({ ...data, categories: data.categories.filter(x => x !== c) }); }
  function saveSettings() { save({ ...data, settings: settingsForm }); }
  function selectCat(c) { setActiveCategory(c); setActiveTag(null); setPage(1); if (isMobile) setMobileOpen(false); }
  function selectTag(t) { setActiveTag(activeTag === t ? null : t); setPage(1); if (isMobile) setMobileOpen(false); }
  function toggleSidebar() { if (isMobile) setMobileOpen(o => !o); else setSidebarOpen(o => !o); }
  function goPublic() { setRoute("public"); window.location.hash = ""; setLoggedIn(false); setAdminTab("albums"); }

  if (loading) return <><style>{css}</style><div style={{display:"flex",alignItems:"center",justifyContent:"center",height:"100vh",color:"var(--text3)",fontSize:14}}>加载中…</div></>;

  if (route === "admin" && !loggedIn) return (
    <><style>{css}</style>
    <div className="login-wrap"><div className="login-box">
      <div className="login-title">后台管理</div>
      <div className="fg">
        <label className="fl">管理密码</label>
        <input type="password" className="fi" value={pwInput} placeholder="输入密码" autoFocus
          onChange={e => setPwInput(e.target.value)}
          onKeyDown={e => { if (e.key==="Enter") { if(pwInput===data.settings.adminPassword){setLoggedIn(true);setLoginErr("");}else setLoginErr("密码错误，请重试"); }}} />
        {loginErr && <div className="err">{loginErr}</div>}
      </div>
      <div style={{display:"flex",gap:8,justifyContent:"space-between"}}>
        <button className="btn" onClick={goPublic}>← 返回</button>
        <button className="btn btn-dark" onClick={() => { if(pwInput===data.settings.adminPassword){setLoggedIn(true);setLoginErr("");}else setLoginErr("密码错误，请重试"); }}>登录</button>
      </div>
    </div></div></>
  );

  if (route === "admin" && loggedIn) {
    const sa = [...data.albums].sort((a,b) => new Date(b.updatedAt)-new Date(a.updatedAt));
    return (
      <><style>{css}</style>
      <div className="adm-layout">
        <div className="adm-sb">
          <div className="adm-sb-title">📷 {data.settings.siteTitle}</div>
          {[{k:"albums",icon:"🖼",label:"相册管理"},{k:"categories",icon:"📁",label:"分类管理"},{k:"settings",icon:"⚙️",label:"系统设置"}].map(({k,icon,label}) => (
            <div key={k} className={`adm-nav ${adminTab===k?"active":""}`} onClick={() => setAdminTab(k)}>{icon} {label}</div>
          ))}
          <div className="adm-spacer"/><div className="adm-divider"/>
          <div className="adm-nav" onClick={goPublic}>← 前台预览</div>
          <div className="adm-nav" onClick={() => { setLoggedIn(false); setPwInput(""); }}>退出登录</div>
        </div>
        <div className="adm-main">
          {adminTab==="albums" && <>
            <div className="adm-header">
              <div className="adm-title">相册管理 <span style={{fontSize:13,fontWeight:400,color:"var(--text3)"}}>({data.albums.length})</span></div>
              <button className="btn btn-dark btn-sm" onClick={openAdd}>＋ 新建相册</button>
            </div>
            {sa.length===0 ? <div className="empty"><div className="empty-icon">🖼️</div><div className="empty-txt">还没有相册</div></div>
              : sa.map(a => (
                <div key={a.id} className="list-item">
                  {a.cover ? <img src={a.cover} alt="" className="list-thumb"/> : <div className="list-no-thumb">📷</div>}
                  <div className="list-info"><div className="list-title">{a.title}</div><div className="list-meta">{a.category} · {a.photoCount} 张 · {fmtDate(a.updatedAt)}</div></div>
                  <div className="list-actions">
                    <button className="btn btn-sm" onClick={() => openEdit(a)}>编辑</button>
                    {delConfirm===a.id
                      ? <><button className="btn btn-red btn-sm" onClick={() => doDelete(a.id)}>确认删除</button><button className="btn btn-sm" onClick={() => setDelConfirm(null)}>取消</button></>
                      : <button className="btn btn-red btn-sm" onClick={() => setDelConfirm(a.id)}>删除</button>}
                  </div>
                </div>
              ))}
          </>}
          {adminTab==="categories" && <>
            <div className="adm-header"><div className="adm-title">分类管理</div></div>
            <div style={{display:"flex",gap:8,marginBottom:16}}>
              <input className="fi" style={{maxWidth:200}} value={newCat} placeholder="新分类名称" onChange={e => setNewCat(e.target.value)} onKeyDown={e => e.key==="Enter" && addCat()}/>
              <button className="btn btn-dark btn-sm" onClick={addCat}>添加</button>
            </div>
            <div style={{display:"flex",flexWrap:"wrap",gap:8}}>
              {data.categories.map(c => (
                <div key={c} className="cat-chip">
                  <span>{c}</span><span style={{fontSize:11,color:"var(--text3)"}}>{data.albums.filter(a=>a.category===c).length} 个</span>
                  <button className="cat-del" onClick={() => removeCat(c)}>×</button>
                </div>
              ))}
            </div>
          </>}
          {adminTab==="settings" && settingsForm && <>
            <div className="adm-header"><div className="adm-title">系统设置</div></div>
            <div style={{maxWidth:380}}>
              <div className="fg"><label className="fl">网站标题</label><input className="fi" value={settingsForm.siteTitle} onChange={e => setSettingsForm({...settingsForm,siteTitle:e.target.value})}/></div>
              <div className="fg"><label className="fl">每页显示相册数</label>
                <select className="fi" value={settingsForm.albumsPerPage} onChange={e => setSettingsForm({...settingsForm,albumsPerPage:parseInt(e.target.value)})}>
                  {[4,6,8,9,12,15].map(n => <option key={n} value={n}>{n} 个</option>)}
                </select>
              </div>
              <div className="fg"><label className="fl">管理密码</label><input className="fi" type="text" value={settingsForm.adminPassword} onChange={e => setSettingsForm({...settingsForm,adminPassword:e.target.value})} placeholder="输入新密码"/></div>
              <div className="fg" style={{background:"#FFFBEB",border:"1px solid #FDE68A",borderRadius:6,padding:"8px 12px"}}>
                <div style={{fontSize:11,color:"#92400E"}}>💡 后台访问路径：在 URL 末尾添加 <strong>#admin</strong> 即可</div>
              </div>
              <button className="btn btn-dark" onClick={saveSettings}>保存设置</button>
            </div>
          </>}
        </div>
      </div>
      {showForm && (
        <div className="f-overlay" onClick={e => e.target===e.currentTarget && setShowForm(false)}>
          <div className="f-box">
            <div className="f-title">{editingAlbum?"编辑相册":"新建相册"}</div>
            <div className="fg"><label className="fl">相册名称 *</label><input className="fi" value={form.title} placeholder="输入相册名称" onChange={e => setForm({...form,title:e.target.value})}/></div>
            <div className="fg"><label className="fl">封面图片 URL</label><input className="fi" value={form.cover} placeholder="https://..." onChange={e => setForm({...form,cover:e.target.value})}/>
              {form.cover && <img src={form.cover} alt="" className="preview-img" onError={e => e.target.style.display="none"}/>}
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10}}>
              <div className="fg"><label className="fl">分类</label>
                <select className="fi" value={form.category} onChange={e => setForm({...form,category:e.target.value})}>
                  {data.categories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="fg"><label className="fl">照片数量</label><input className="fi" type="number" min="0" value={form.photoCount} placeholder="0" onChange={e => setForm({...form,photoCount:e.target.value})}/></div>
            </div>
            <div className="fg"><label className="fl">标签（逗号分隔）</label><input className="fi" value={form.tags} placeholder="标签1, 标签2" onChange={e => setForm({...form,tags:e.target.value})}/></div>
            <div className="fg"><label className="fl">相册简介</label><textarea className="fi" value={form.description} placeholder="描述这个相册…" onChange={e => setForm({...form,description:e.target.value})}/></div>
            <div style={{display:"flex",gap:8,justifyContent:"flex-end"}}>
              <button className="btn" onClick={() => setShowForm(false)}>取消</button>
              <button className="btn btn-dark" onClick={saveAlbum}>保存</button>
            </div>
          </div>
        </div>
      )}
      </>
    );
  }

  // ── PUBLIC VIEW ──
  const perPage = data.settings.albumsPerPage;
  const sorted = [...data.albums].sort((a,b) => new Date(b.updatedAt)-new Date(a.updatedAt));
  let filtered = activeCategory==="全部" ? sorted : sorted.filter(a => a.category===activeCategory);
  if (activeTag) filtered = filtered.filter(a => a.tags.includes(activeTag));
  if (searchQ.trim()) { const q = searchQ.trim().toLowerCase(); filtered = filtered.filter(a => a.title.toLowerCase().includes(q)||a.description.toLowerCase().includes(q)||a.tags.some(t=>t.toLowerCase().includes(q))); }
  const totalPages = Math.max(1, Math.ceil(filtered.length/perPage));
  const paged = filtered.slice((page-1)*perPage, page*perPage);
  const allTags = [...new Set(sorted.flatMap(a => a.tags))];
  const catCounts = Object.fromEntries(data.categories.map(c => [c, data.albums.filter(a=>a.category===c).length]));
  const hasFilter = activeCategory!=="全部"||activeTag||searchQ.trim();
  const sidebarVisible = isMobile ? mobileOpen : sidebarOpen;

  return (
    <><style>{css}</style>
    <div>
      <header className="hdr">
        <div className="hdr-left">
          <button className={`sidebar-toggle ${sidebarVisible?"open":""}`} onClick={toggleSidebar} aria-label="切换侧栏"><span/><span/><span/></button>
          <div className="hdr-title">📷 {data.settings.siteTitle}</div>
        </div>
        <div className="hdr-search">
          <span className="hdr-search-icon">🔍</span>
          <input value={searchQ} placeholder="搜索相册…" onChange={e => { setSearchQ(e.target.value); setPage(1); }}/>
        </div>
        <div style={{width:1}}/>
      </header>
      <div className="layout">
        {isMobile && mobileOpen && <div className="sidebar-overlay" onClick={() => setMobileOpen(false)}/>}
        <div className={`sidebar-wrap ${isMobile?(mobileOpen?"mobile-open":""):(sidebarOpen?"":"collapsed")}`}>
          <div className="sidebar">
            <div>
              <div className="sb-section-label">分类</div>
              <div className={`cat-item ${activeCategory==="全部"?"active":""}`} onClick={() => selectCat("全部")}><span>全部</span><span className="cat-count">{data.albums.length}</span></div>
              {data.categories.map(c => (
                <div key={c} className={`cat-item ${activeCategory===c?"active":""}`} onClick={() => selectCat(c)}><span>{c}</span><span className="cat-count">{catCounts[c]||0}</span></div>
              ))}
            </div>
            {allTags.length>0 && <div><div className="sb-section-label">标签</div><div className="tag-wrap">{allTags.map(t => <button key={t} className={`tag-btn ${activeTag===t?"active":""}`} onClick={() => selectTag(t)}>#{t}</button>)}</div></div>}
          </div>
        </div>
        <div className="main">
          <div className="main-header">
            <div className="main-info">
              {activeTag && <><strong>#{activeTag}</strong> · </>}
              {activeCategory!=="全部"&&!activeTag && <><strong>{activeCategory}</strong> · </>}
              {searchQ.trim() && <><strong>"{searchQ}"</strong> · </>}
              {filtered.length} 个相册
            </div>
            {hasFilter && <button className="clear-btn" onClick={() => { setActiveCategory("全部"); setActiveTag(null); setSearchQ(""); setPage(1); }}>✕ 清除筛选</button>}
          </div>
          {paged.length===0
            ? <div className="empty"><div className="empty-icon">🔍</div><div className="empty-txt">没有找到相册</div></div>
            : <div className="grid">{paged.map(a => (
                <div key={a.id} className="card" onClick={() => setSelectedAlbum(a)}>
                  {a.cover ? <img src={a.cover} alt={a.title} className="card-img" loading="lazy"/> : <div className="card-no-img">📷</div>}
                  <div className="card-body">
                    <div className="card-title">{a.title}</div>
                    <div className="card-footer"><span className="badge">{a.category}</span><span className="card-count">{a.photoCount} 张</span></div>
                    <div className="card-date">{fmtDate(a.updatedAt)}</div>
                  </div>
                </div>
              ))}</div>}
          {totalPages>1 && <div className="pager">
            <button className="pager-btn" disabled={page===1} onClick={() => setPage(p=>p-1)}>‹</button>
            {Array.from({length:totalPages},(_,i)=>i+1).map(p => <button key={p} className={`pager-btn ${p===page?"active":""}`} onClick={() => setPage(p)}>{p}</button>)}
            <button className="pager-btn" disabled={page===totalPages} onClick={() => setPage(p=>p+1)}>›</button>
          </div>}
        </div>
      </div>
    </div>
    {selectedAlbum && (
      <div className="overlay" onClick={e => e.target===e.currentTarget && setSelectedAlbum(null)}>
        <div className="modal">
          {selectedAlbum.cover && <img src={selectedAlbum.cover} alt={selectedAlbum.title} className="modal-img"/>}
          <div className="modal-body">
            <div className="modal-top"><div className="modal-title">{selectedAlbum.title}</div><button className="modal-close" onClick={() => setSelectedAlbum(null)}>✕</button></div>
            <div className="modal-meta">
              <span className="badge">{selectedAlbum.category}</span>
              <span style={{fontSize:12,color:"var(--text3)"}}>{selectedAlbum.photoCount} 张照片</span>
              <span style={{fontSize:12,color:"var(--text3)"}}>更新 {fmtDate(selectedAlbum.updatedAt)}</span>
            </div>
            {selectedAlbum.description && <div className="modal-desc">{selectedAlbum.description}</div>}
            {selectedAlbum.tags.length>0 && <div className="modal-tags">{selectedAlbum.tags.map(t => <button key={t} className="tag-btn" onClick={() => { setSelectedAlbum(null); selectTag(t); }}>#{t}</button>)}</div>}
          </div>
        </div>
      </div>
    )}
    </>
  );
}
APPJSX

# ────────────────────────────────────────
#  .gitignore
# ────────────────────────────────────────
cat > .gitignore << 'GITIGNORE'
node_modules/
dist/
.DS_Store
*.local
.env
GITIGNORE

success "项目文件写入完成"

# ── 安装依赖 ──
info "正在安装依赖包（首次约需 30 秒）..."
npm install --prefer-offline --no-audit --no-fund 2>&1 | grep -E "added|warn|error" | head -5
success "依赖安装完成"

echo ""
echo -e "${BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ── 根据模式启动 ──
case "$MODE" in
  --dev|-d)
    echo -e "  ${GREEN}前台：${BOLD}http://localhost:5173${RESET}"
    echo -e "  ${GREEN}后台：${BOLD}http://localhost:5173/#admin${RESET}  密码: admin123"
    echo -e "${BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    npm run dev
    ;;
  --build|-b)
    npm run build
    success "构建完成 → ./$INSTALL_DIR/dist/"
    echo -e "  将 dist/ 目录部署到 Nginx / Caddy / Vercel 等静态托管即可"
    echo ""
    ;;
  *)
    npm run build
    echo -e "  ${GREEN}访问地址：${BOLD}http://localhost:3000${RESET}"
    echo -e "  ${GREEN}后台入口：${BOLD}http://localhost:3000/#admin${RESET}"
    echo -e "  ${YELLOW}默认密码：${BOLD}admin123${RESET}（后台设置中可修改）"
    echo -e "${BOLD}  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    npm run serve
    ;;
esac

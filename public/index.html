<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>公开相册 - Public Album</title>
    <style>
        :root {
            --bg: #f5f5f5;
            --card-bg: #fff;
            --text: #333;
            --text-secondary: #777;
            --border: #e0e0e0;
            --shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
            --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.15);
            --accent: #4a90d9;
            --accent-hover: #357abd;
            --danger: #e05555;
            --danger-hover: #c74444;
            --overlay: rgba(0, 0, 0, 0.9);
            --radius: 12px;
            --radius-sm: 8px;
            --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            --max-width: 1400px;
            --header-height: 60px;
            --gap: 16px;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --bg: #1a1a1f;
                --card-bg: #252530;
                --text: #e0e0e0;
                --text-secondary: #aaa;
                --border: #3a3a45;
                --shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
                --shadow-hover: 0 8px 30px rgba(0, 0, 0, 0.5);
                --accent: #5ba0e8;
                --accent-hover: #4a90d9;
                --overlay: rgba(0, 0, 0, 0.95);
            }
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            transition: background var(--transition), color var(--transition);
        }

        /* Header */
        .header {
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            height: var(--header-height);
            display: flex;
            align-items: center;
            padding: 0 20px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
            transition: background var(--transition), border var(--transition);
        }
        .header-inner {
            max-width: var(--max-width);
            width: 100%;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }
        .logo {
            font-size: 1.35rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }
        .logo svg {
            width: 28px;
            height: 28px;
            flex-shrink: 0;
        }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all var(--transition);
            text-decoration: none;
            white-space: nowrap;
            font-family: inherit;
        }
        .btn-outline {
            background: transparent;
            border: 1.5px solid var(--border);
            color: var(--text);
        }
        .btn-outline:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(74, 144, 217, 0.04);
        }
        .btn-primary {
            background: var(--accent);
            color: #fff;
            border: 1.5px solid var(--accent);
        }
        .btn-primary:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
        }
        .btn-danger {
            background: var(--danger);
            color: #fff;
            border: 1.5px solid var(--danger);
        }
        .btn-danger:hover {
            background: var(--danger-hover);
            border-color: var(--danger-hover);
        }
        .btn-sm {
            padding: 5px 12px;
            font-size: 0.8rem;
            border-radius: 16px;
        }
        .btn-icon {
            width: 36px;
            height: 36px;
            padding: 0;
            border-radius: 50%;
            justify-content: center;
            font-size: 1.1rem;
        }

        /* Album Tabs */
        .album-tabs {
            max-width: var(--max-width);
            margin: 16px auto 0;
            padding: 0 20px;
            display: flex;
            gap: 8px;
            overflow-x: auto;
            scrollbar-width: none;
            -ms-overflow-style: none;
            flex-wrap: nowrap;
            align-items: center;
        }
        .album-tabs::-webkit-scrollbar {
            display: none;
        }
        .album-tab {
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 0.9rem;
            cursor: pointer;
            border: 1.5px solid transparent;
            background: var(--card-bg);
            color: var(--text-secondary);
            white-space: nowrap;
            transition: all var(--transition);
            font-family: inherit;
            flex-shrink: 0;
            user-select: none;
        }
        .album-tab:hover {
            color: var(--text);
            border-color: var(--border);
        }
        .album-tab.active {
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
            font-weight: 600;
        }
        .album-tab-count {
            font-size: 0.75rem;
            opacity: 0.8;
            margin-left: 2px;
        }

        /* Gallery Grid */
        .gallery-container {
            max-width: var(--max-width);
            margin: 20px auto;
            padding: 0 20px;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: var(--gap);
        }
        @media (min-width: 1600px) {
            .gallery {
                grid-template-columns: repeat(5, 1fr);
            }
        }
        @media (max-width: 768px) {
            .gallery {
                grid-template-columns: repeat(2, 1fr);
                gap: 8px;
            }
            :root {
                --gap: 8px;
                --header-height: 52px;
            }
            .header {
                padding: 0 12px;
            }
            .logo {
                font-size: 1.1rem;
            }
            .btn {
                padding: 6px 12px;
                font-size: 0.8rem;
            }
            .album-tabs {
                padding: 0 12px;
                margin-top: 8px;
                gap: 4px;
            }
            .album-tab {
                padding: 6px 14px;
                font-size: 0.8rem;
            }
            .gallery-container {
                padding: 0 12px;
                margin-top: 12px;
            }
        }
        @media (max-width: 400px) {
            .gallery {
                grid-template-columns: 1fr 1fr;
                gap: 6px;
            }
            .header-inner {
                gap: 8px;
            }
            .btn {
                padding: 5px 10px;
                font-size: 0.75rem;
                border-radius: 16px;
            }
        }

        /* Photo Card */
        .photo-card {
            position: relative;
            border-radius: var(--radius);
            overflow: hidden;
            background: var(--card-bg);
            box-shadow: var(--shadow);
            cursor: pointer;
            transition: all var(--transition);
            aspect-ratio: 4/3;
            group: true;
            break-inside: avoid;
        }
        .photo-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-hover);
        }
        .photo-card:active {
            transform: scale(0.98);
        }
        .photo-card img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: transform 0.4s ease;
            background: #e8e8e8;
        }
        .photo-card:hover img {
            transform: scale(1.05);
        }
        .photo-card-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 24px 12px 12px;
            background: linear-gradient(transparent, rgba(0, 0, 0, 0.6));
            opacity: 0;
            transition: opacity var(--transition);
            pointer-events: none;
        }
        .photo-card:hover .photo-card-overlay {
            opacity: 1;
        }
        .photo-card-title {
            color: #fff;
            font-size: 0.85rem;
            font-weight: 500;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Admin highlight on cards */
        .photo-card.admin-mode .photo-card-overlay {
            opacity: 1;
            background: linear-gradient(transparent, rgba(200, 50, 50, 0.7));
        }
        .photo-card.admin-mode .photo-card-title::after {
            content: ' ✕';
            font-size: 0.7rem;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
            grid-column: 1 / -1;
        }
        .empty-state svg {
            width: 80px;
            height: 80px;
            opacity: 0.4;
            margin-bottom: 16px;
        }
        .empty-state h3 {
            font-size: 1.2rem;
            margin-bottom: 8px;
            color: var(--text);
        }

        /* Loading Skeleton */
        .skeleton {
            border-radius: var(--radius);
            background: var(--card-bg);
            box-shadow: var(--shadow);
            aspect-ratio: 4/3;
            animation: shimmer 1.5s infinite;
            background: linear-gradient(90deg, var(--card-bg) 25%, var(--border) 50%, var(--card-bg) 75%);
            background-size: 200% 100%;
        }
        @keyframes shimmer {
            0% {
                background-position: 200% 0;
            }
            100% {
                background-position: -200% 0;
            }
        }

        /* Lightbox */
        .lightbox {
            position: fixed;
            inset: 0;
            z-index: 9999;
            background: var(--overlay);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
            -webkit-tap-highlight-color: transparent;
        }
        .lightbox.active {
            opacity: 1;
            pointer-events: auto;
        }
        .lightbox-content {
            position: relative;
            max-width: 90vw;
            max-height: 85vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .lightbox img {
            max-width: 90vw;
            max-height: 85vh;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            user-select: none;
            -webkit-user-drag: none;
        }
        .lightbox-close {
            position: absolute;
            top: 16px;
            right: 20px;
            z-index: 10;
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
            border: none;
            color: #fff;
            font-size: 1.5rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background var(--transition);
        }
        .lightbox-close:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .lightbox-nav {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            z-index: 10;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.15);
            border: none;
            color: #fff;
            font-size: 1.5rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background var(--transition);
        }
        .lightbox-nav:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .lightbox-nav.prev {
            left: 12px;
        }
        .lightbox-nav.next {
            right: 12px;
        }
        .lightbox-info {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: #fff;
            font-size: 0.9rem;
            background: rgba(0, 0, 0, 0.5);
            padding: 6px 16px;
            border-radius: 20px;
            pointer-events: none;
        }
        @media (max-width: 768px) {
            .lightbox-nav {
                width: 36px;
                height: 36px;
                font-size: 1.1rem;
            }
            .lightbox-nav.prev {
                left: 4px;
            }
            .lightbox-nav.next {
                right: 4px;
            }
            .lightbox-close {
                top: 8px;
                right: 8px;
                width: 36px;
                height: 36px;
                font-size: 1.2rem;
            }
            .lightbox img {
                max-width: 95vw;
                max-height: 80vh;
            }
        }

        /* Modal */
        .modal-overlay {
            position: fixed;
            inset: 0;
            z-index: 9000;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
            padding: 20px;
        }
        .modal-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }
        .modal {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
            width: 100%;
            max-width: 500px;
            max-height: 85vh;
            overflow-y: auto;
            padding: 24px;
            position: relative;
            transition: transform 0.25s ease;
            transform: translateY(20px);
        }
        .modal-overlay.active .modal {
            transform: translateY(0);
        }
        .modal h3 {
            font-size: 1.3rem;
            margin-bottom: 20px;
        }
        .modal-close {
            position: absolute;
            top: 12px;
            right: 16px;
            background: none;
            border: none;
            font-size: 1.4rem;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 4px 8px;
            border-radius: 4px;
        }
        .modal-close:hover {
            color: var(--text);
            background: var(--border);
        }
        .form-group {
            margin-bottom: 16px;
        }
        .form-group label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--text);
        }
        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 10px 14px;
            border: 1.5px solid var(--border);
            border-radius: var(--radius-sm);
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--bg);
            color: var(--text);
            transition: border var(--transition);
            resize: vertical;
        }
        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(74, 144, 217, 0.1);
        }
        .form-group textarea {
            min-height: 80px;
        }
        .form-hint {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }
        .form-actions {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .upload-zone {
            border: 2px dashed var(--border);
            border-radius: var(--radius);
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all var(--transition);
            background: var(--bg);
        }
        .upload-zone:hover,
        .upload-zone.drag-over {
            border-color: var(--accent);
            background: rgba(74, 144, 217, 0.04);
        }
        .upload-zone svg {
            width: 40px;
            height: 40px;
            opacity: 0.5;
            margin-bottom: 8px;
        }
        .upload-zone p {
            font-size: 0.9rem;
            color: var(--text-secondary);
        }
        .upload-preview {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        .upload-preview-item {
            width: 60px;
            height: 60px;
            border-radius: 6px;
            object-fit: cover;
            border: 2px solid var(--border);
        }

        /* Toast */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 99999;
            display: flex;
            flex-direction: column;
            gap: 8px;
            pointer-events: none;
        }
        .toast {
            padding: 12px 18px;
            border-radius: var(--radius-sm);
            color: #fff;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            animation: slideIn 0.3s ease, fadeOut 0.3s ease 2.5s forwards;
            pointer-events: auto;
            max-width: 350px;
        }
        .toast.success {
            background: #4caf84;
        }
        .toast.error {
            background: #e05555;
        }
        .toast.info {
            background: #5ba0e8;
        }
        @keyframes slideIn {
            from {
                transform: translateX(120%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes fadeOut {
            to {
                opacity: 0;
                transform: translateY(-10px);
            }
        }

        /* Settings bar */
        .settings-bar {
            max-width: var(--max-width);
            margin: 8px auto 0;
            padding: 0 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.8rem;
            color: var(--text-secondary);
            flex-wrap: wrap;
        }
        .settings-bar span {
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            background: #e8f4e8;
            color: #3a8;
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header class="header">
        <div class="header-inner">
            <a href="/" class="logo">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                </svg>
                公开相册
            </a>
            <div class="header-actions">
                <button class="btn btn-outline btn-sm" id="btnManage" title="管理相册">🔧 管理</button>
                <button class="btn btn-outline btn-sm" id="btnAddAlbum" title="新建相册" style="display:none;">📁 新建</button>
                <button class="btn btn-primary btn-sm" id="btnAddPhoto" title="添加图片" style="display:none;">📷 添加图片</button>
                <button class="btn btn-outline btn-sm" id="btnSettings" title="图床设置" style="display:none;">⚙️ 设置</button>
                <button class="btn btn-outline btn-sm" id="btnLogout" style="display:none;">退出</button>
            </div>
        </div>
    </header>

    <!-- Album Tabs -->
    <nav class="album-tabs" id="albumTabs">
        <button class="album-tab active" data-album="all">📷 全部</button>
    </nav>

    <!-- Settings bar -->
    <div class="settings-bar" id="settingsBar">
        <span>存储模式：<strong id="storageModeLabel">本地存储</strong></span>
    </div>

    <!-- Gallery -->
    <main class="gallery-container">
        <div class="gallery" id="gallery">
            <!-- Dynamic content -->
        </div>
    </main>

    <!-- Lightbox -->
    <div class="lightbox" id="lightbox">
        <button class="lightbox-close" id="lightboxClose">✕</button>
        <button class="lightbox-nav prev" id="lightboxPrev">◀</button>
        <button class="lightbox-nav next" id="lightboxNext">▶</button>
        <div class="lightbox-content" id="lightboxContent"></div>
        <div class="lightbox-info" id="lightboxInfo"></div>
    </div>

    <!-- Modal: Auth -->
    <div class="modal-overlay" id="modalAuth">
        <div class="modal">
            <button class="modal-close" id="modalAuthClose">✕</button>
            <h3>🔐 管理员验证</h3>
            <div class="form-group">
                <label>管理密码</label>
                <input type="password" id="authPassword" placeholder="请输入管理密码" autocomplete="off">
            </div>
            <div class="form-actions">
                <button class="btn btn-outline btn-sm" id="modalAuthCancel">取消</button>
                <button class="btn btn-primary btn-sm" id="modalAuthConfirm">验证</button>
            </div>
            <p class="form-hint" style="margin-top:12px;">默认密码：<code>admin123</code>，请及时修改。</p>
        </div>
    </div>

    <!-- Modal: Add Album -->
    <div class="modal-overlay" id="modalAlbum">
        <div class="modal">
            <button class="modal-close" id="modalAlbumClose">✕</button>
            <h3 id="modalAlbumTitle">📁 新建相册</h3>
            <input type="hidden" id="editAlbumId">
            <div class="form-group">
                <label>相册名称</label>
                <input type="text" id="albumName" placeholder="输入相册名称" maxlength="50">
            </div>
            <div class="form-group">
                <label>描述（可选）</label>
                <textarea id="albumDesc" placeholder="简短描述这个相册" maxlength="200"></textarea>
            </div>
            <div class="form-actions">
                <button class="btn btn-outline btn-sm" id="modalAlbumCancel">取消</button>
                <button class="btn btn-danger btn-sm" id="modalAlbumDelete" style="display:none;">删除相册</button>
                <button class="btn btn-primary btn-sm" id="modalAlbumSave">保存</button>
            </div>
        </div>
    </div>

    <!-- Modal: Add Photo -->
    <div class="modal-overlay" id="modalPhoto">
        <div class="modal">
            <button class="modal-close" id="modalPhotoClose">✕</button>
            <h3>📷 添加图片</h3>
            <div class="form-group">
                <label>所属相册</label>
                <select id="photoAlbumSelect"></select>
            </div>
            <div class="form-group">
                <label>上传文件</label>
                <div class="upload-zone" id="uploadZone">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    <p>点击或拖拽图片到此处</p>
                    <p style="font-size:0.7rem;opacity:0.7;">支持 JPG/PNG/WebP/GIF，单文件最大20MB</p>
                </div>
                <input type="file" id="photoFileInput" accept="image/*" multiple style="display:none;">
                <div class="upload-preview" id="uploadPreview"></div>
            </div>
            <div class="form-group">
                <label>或直接粘贴图片URL（图床链接）</label>
                <textarea id="photoUrlInput" placeholder="https://example.com/image.jpg&#10;每行一个URL，可批量添加" rows="3"></textarea>
                <p class="form-hint">支持对接任意图床，直接粘贴图床返回的图片链接即可。</p>
            </div>
            <div class="form-group">
                <label>标题（可选）</label>
                <input type="text" id="photoTitle" placeholder="图片标题，留空则使用文件名" maxlength="100">
            </div>
            <div class="form-actions">
                <button class="btn btn-outline btn-sm" id="modalPhotoCancel">取消</button>
                <button class="btn btn-primary btn-sm" id="modalPhotoSave">添加</button>
            </div>
        </div>
    </div>

    <!-- Modal: Settings -->
    <div class="modal-overlay" id="modalSettings">
        <div class="modal">
            <button class="modal-close" id="modalSettingsClose">✕</button>
            <h3>⚙️ 系统设置</h3>
            <div class="form-group">
                <label>图片存储模式</label>
                <select id="settingStorageMode">
                    <option value="local">本地存储（图片保存在服务器）</option>
                    <option value="smms">SM.MS 图床（需API Token）</option>
                    <option value="url_only">仅URL模式（不存储文件，仅记录链接）</option>
                </select>
                <p class="form-hint">"仅URL模式"下，所有图片通过粘贴图床URL添加，适合对接任意图床。</p>
            </div>
            <div class="form-group" id="smmsTokenGroup" style="display:none;">
                <label>SM.MS API Token</label>
                <input type="text" id="settingSmmsToken" placeholder="输入SM.MS的API Token">
                <p class="form-hint">在 <a href="https://sm.ms/home/apitoken" target="_blank" rel="noopener">sm.ms</a> 获取Token</p>
            </div>
            <div class="form-group">
                <label>修改管理密码</label>
                <input type="password" id="settingNewPassword" placeholder="留空则不修改" autocomplete="off">
            </div>
            <div class="form-actions">
                <button class="btn btn-outline btn-sm" id="modalSettingsCancel">取消</button>
                <button class="btn btn-primary btn-sm" id="modalSettingsSave">保存设置</button>
            </div>
        </div>
    </div>

    <!-- Toast container -->
    <div class="toast-container" id="toastContainer"></div>

    <script>
        // ==================== 全局状态 ====================
        const STATE = {
            isAdmin: false,
            adminToken: '',
            albums: [],
            photos: [],
            currentAlbumId: 'all',
            lightboxIndex: -1,
            lightboxPhotos: [],
            storageMode: 'local',
            pendingFiles: [],
        };

        // ==================== DOM引用 ====================
        const $ = (sel) => document.querySelector(sel);
        const $$ = (sel) => document.querySelectorAll(sel);

        const dom = {
            gallery: $('#gallery'),
            albumTabs: $('#albumTabs'),
            lightbox: $('#lightbox'),
            lightboxContent: $('#lightboxContent'),
            lightboxInfo: $('#lightboxInfo'),
            btnManage: $('#btnManage'),
            btnAddAlbum: $('#btnAddAlbum'),
            btnAddPhoto: $('#btnAddPhoto'),
            btnSettings: $('#btnSettings'),
            btnLogout: $('#btnLogout'),
            settingsBar: $('#settingsBar'),
            storageModeLabel: $('#storageModeLabel'),
            toastContainer: $('#toastContainer'),
            // Modals
            modalAuth: $('#modalAuth'),
            modalAlbum: $('#modalAlbum'),
            modalPhoto: $('#modalPhoto'),
            modalSettings: $('#modalSettings'),
            // Upload
            uploadZone: $('#uploadZone'),
            photoFileInput: $('#photoFileInput'),
            uploadPreview: $('#uploadPreview'),
            photoUrlInput: $('#photoUrlInput'),
            photoAlbumSelect: $('#photoAlbumSelect'),
            photoTitle: $('#photoTitle'),
            // Settings
            settingStorageMode: $('#settingStorageMode'),
            settingSmmsToken: $('#settingSmmsToken'),
            smmsTokenGroup: $('#smmsTokenGroup'),
            settingNewPassword: $('#settingNewPassword'),
        };

        // ==================== API封装 ====================
        const API = {
            async request(path, options = {}) {
                const url = path.startsWith('http') ? path : `/api${path}`;
                const headers = { ...options.headers };
                if (STATE.adminToken) headers['X-Admin-Token'] = STATE.adminToken;
                if (!(options.body instanceof FormData)) {
                    headers['Content-Type'] = 'application/json';
                }
                const resp = await fetch(url, {
                    ...options,
                    headers,
                });
                const data = await resp.json();
                if (!resp.ok && data.detail) {
                    throw new Error(data.detail);
                }
                return data;
            },
            getAlbums() { return this.request('/albums'); },
            getPhotos(albumId) {
                const params = albumId && albumId !== 'all' ? `?album_id=${albumId}` : '';
                return this.request(`/photos${params}`);
            },
            auth(password) {
                return this.request('/auth', {
                    method: 'POST',
                    body: JSON.stringify({ password }),
                });
            },
            verifyToken() {
                return this.request('/verify-token');
            },
            createAlbum(data) {
                return this.request('/albums', { method: 'POST', body: JSON.stringify(data) });
            },
            updateAlbum(id, data) {
                return this.request(`/albums/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            },
            deleteAlbum(id) {
                return this.request(`/albums/${id}`, { method: 'DELETE' });
            },
            createPhoto(formData) {
                return this.request('/photos', {
                    method: 'POST',
                    body: formData,
                    headers: {},
                });
            },
            createPhotoByUrl(data) {
                return this.request('/photos/url', { method: 'POST', body: JSON.stringify(data) });
            },
            deletePhoto(id) {
                return this.request(`/photos/${id}`, { method: 'DELETE' });
            },
            getSettings() {
                return this.request('/settings');
            },
            updateSettings(data) {
                return this.request('/settings', { method: 'PUT', body: JSON.stringify(data) });
            },
        };

        // ==================== Toast ====================
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            dom.toastContainer.appendChild(toast);
            setTimeout(() => toast.remove(), 3000);
        }

        // ==================== 模态框工具 ====================
        function openModal(modalEl) {
            modalEl.classList.add('active');
        }

        function closeModal(modalEl) {
            modalEl.classList.remove('active');
        }

        function closeAllModals() {
            [dom.modalAuth, dom.modalAlbum, dom.modalPhoto, dom.modalSettings].forEach(closeModal);
        }

        // ==================== 认证 ====================
        async function checkAdmin() {
            const token = localStorage.getItem('admin_token');
            if (token) {
                STATE.adminToken = token;
                try {
                    await API.verifyToken();
                    STATE.isAdmin = true;
                    updateAdminUI();
                    return;
                } catch (e) {
                    STATE.adminToken = '';
                    localStorage.removeItem('admin_token');
                }
            }
            STATE.isAdmin = false;
            updateAdminUI();
        }

        function updateAdminUI() {
            const adminBtns = [dom.btnAddAlbum, dom.btnAddPhoto, dom.btnSettings, dom.btnLogout];
            adminBtns.forEach(b => b.style.display = STATE.isAdmin ? '' : 'none');
            dom.btnManage.style.display = STATE.isAdmin ? 'none' : '';
            dom.settingsBar.style.display = STATE.isAdmin ? '' : 'flex';

            // Update gallery cards
            document.querySelectorAll('.photo-card').forEach(card => {
                card.classList.toggle('admin-mode', STATE.isAdmin);
            });
        }

        async function handleAuth(password) {
            try {
                const data = await API.auth(password);
                STATE.adminToken = data.token;
                STATE.isAdmin = true;
                localStorage.setItem('admin_token', data.token);
                updateAdminUI();
                closeModal(dom.modalAuth);
                showToast('验证成功，已进入管理模式', 'success');
                await loadAll();
            } catch (e) {
                showToast(e.message || '密码错误', 'error');
            }
        }

        function logout() {
            STATE.isAdmin = false;
            STATE.adminToken = '';
            localStorage.removeItem('admin_token');
            updateAdminUI();
            STATE.currentAlbumId = 'all';
            updateAlbumTabs();
            renderGallery();
            showToast('已退出管理模式', 'info');
        }

        // ==================== 数据加载 ====================
        async function loadAlbums() {
            try {
                const data = await API.getAlbums();
                STATE.albums = data.albums || [];
                updateAlbumTabs();
                updatePhotoAlbumSelect();
            } catch (e) {
                console.error('加载相册失败:', e);
                STATE.albums = [];
            }
        }

        async function loadPhotos() {
            dom.gallery.innerHTML =
                '<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
            try {
                const data = await API.getPhotos(STATE.currentAlbumId);
                STATE.photos = data.photos || [];
            } catch (e) {
                console.error('加载图片失败:', e);
                STATE.photos = [];
            }
            renderGallery();
        }

        async function loadSettings() {
            try {
                const data = await API.getSettings();
                STATE.storageMode = data.storage_mode || 'local';
                dom.storageModeLabel.textContent =
                    STATE.storageMode === 'local' ? '本地存储' :
                    STATE.storageMode === 'smms' ? 'SM.MS图床' : '仅URL模式';
                dom.settingStorageMode.value = STATE.storageMode;
                dom.settingSmmsToken.value = data.smms_token || '';
                updateSmmsTokenVisibility();
            } catch (e) {
                console.error('加载设置失败:', e);
            }
        }

        async function loadAll() {
            await Promise.all([loadAlbums(), loadPhotos(), loadSettings()]);
        }

        function updateSmmsTokenVisibility() {
            dom.smmsTokenGroup.style.display = dom.settingStorageMode.value === 'smms' ? '' : 'none';
        }

        // ==================== 渲染 ====================
        function updateAlbumTabs() {
            const tabsContainer = dom.albumTabs;
            let html = '<button class="album-tab" data-album="all">📷 全部</button>';
            STATE.albums.forEach(album => {
                const count = STATE.photos.filter(p => p.album_id === album.id).length;
                html +=
                    `<button class="album-tab" data-album="${album.id}">${escapeHtml(album.name)}<span class="album-tab-count">(${count})</span></button>`;
            });
            tabsContainer.innerHTML = html;

            // Highlight active
            const activeTab = tabsContainer.querySelector(`[data-album="${STATE.currentAlbumId}"]`);
            if (activeTab) activeTab.classList.add('active');
            else tabsContainer.querySelector('[data-album="all"]')?.classList.add('active');

            // Click handlers
            tabsContainer.querySelectorAll('.album-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    STATE.currentAlbumId = tab.dataset.album;
                    updateAlbumTabs();
                    loadPhotos();
                });
            });

            // Long press on album tab to edit (admin mode)
            if (STATE.isAdmin) {
                tabsContainer.querySelectorAll('.album-tab[data-album]:not([data-album="all"])').forEach(
                tab => {
                    tab.addEventListener('dblclick', (e) => {
                        const albumId = parseInt(tab.dataset.album);
                        const album = STATE.albums.find(a => a.id === albumId);
                        if (album) openEditAlbumModal(album);
                    });
                    // Touch long press
                    let longPressTimer;
                    tab.addEventListener('touchstart', (e) => {
                        const albumId = parseInt(tab.dataset.album);
                        longPressTimer = setTimeout(() => {
                            const album = STATE.albums.find(a => a.id === albumId);
                            if (album) openEditAlbumModal(album);
                        }, 600);
                    });
                    tab.addEventListener('touchend', () => clearTimeout(longPressTimer));
                    tab.addEventListener('touchmove', () => clearTimeout(longPressTimer));
                });
            }
        }

        function updatePhotoAlbumSelect() {
            let html = '';
            STATE.albums.forEach(a => {
                html += `<option value="${a.id}">${escapeHtml(a.name)}</option>`;
            });
            if (!STATE.albums.length) {
                html = '<option value="">请先创建相册</option>';
            }
            dom.photoAlbumSelect.innerHTML = html;
        }

        function renderGallery() {
            if (!STATE.photos.length) {
                dom.gallery.innerHTML = `
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.5"/>
                            <polyline points="21 15 16 10 5 21"/>
                        </svg>
                        <h3>暂无图片</h3>
                        <p>${STATE.isAdmin ? '点击"添加图片"按钮开始上传吧' : '相册还是空的，敬请期待'}</p>
                    </div>`;
                return;
            }
            dom.gallery.innerHTML = STATE.photos.map((photo, index) => `
                <div class="photo-card ${STATE.isAdmin ? 'admin-mode' : ''}"
                     data-index="${index}"
                     data-id="${photo.id}"
                     title="${escapeHtml(photo.title || '')}">
                    <img src="${escapeHtml(photo.url)}"
                         alt="${escapeHtml(photo.title || '图片')}"
                         loading="lazy"
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 200 150%22><rect fill=%22%23e0e0e0%22 width=%22200%22 height=%22150%22/><text x=%22100%22 y=%2280%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2214%22>加载失败</text></svg>'">
                    <div class="photo-card-overlay">
                        <span class="photo-card-title">${escapeHtml(photo.title || '无标题')}</span>
                    </div>
                </div>
            `).join('');

            // Click to open lightbox
            dom.gallery.querySelectorAll('.photo-card').forEach(card => {
                card.addEventListener('click', (e) => {
                    if (STATE.isAdmin) {
                        // In admin mode, click to delete
                        const photoId = parseInt(card.dataset.id);
                        const photoTitle = STATE.photos.find(p => p.id === photoId)?.title ||
                            '图片';
                        if (confirm(`确定要删除「${photoTitle}」吗？此操作不可恢复。`)) {
                            deletePhoto(photoId);
                        }
                        return;
                    }
                    const index = parseInt(card.dataset.index);
                    openLightbox(index);
                });
            });
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        // ==================== 灯箱 ====================
        function openLightbox(index) {
            STATE.lightboxPhotos = STATE.photos;
            STATE.lightboxIndex = index;
            showLightboxImage();
            dom.lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeLightbox() {
            dom.lightbox.classList.remove('active');
            document.body.style.overflow = '';
            STATE.lightboxIndex = -1;
        }

        function showLightboxImage() {
            const photo = STATE.lightboxPhotos[STATE.lightboxIndex];
            if (!photo) return;
            dom.lightboxContent.innerHTML = `<img src="${escapeHtml(photo.url)}" alt="${escapeHtml(photo.title || '')}">`;
            dom.lightboxInfo.textContent =
                `${photo.title || '无标题'} (${STATE.lightboxIndex + 1}/${STATE.lightboxPhotos.length})`;
        }

        function lightboxNext() {
            if (STATE.lightboxPhotos.length === 0) return;
            STATE.lightboxIndex = (STATE.lightboxIndex + 1) % STATE.lightboxPhotos.length;
            showLightboxImage();
        }

        function lightboxPrev() {
            if (STATE.lightboxPhotos.length === 0) return;
            STATE.lightboxIndex = (STATE.lightboxIndex - 1 + STATE.lightboxPhotos.length) % STATE.lightboxPhotos
                .length;
            showLightboxImage();
        }

        // ==================== 删除图片 ====================
        async function deletePhoto(photoId) {
            try {
                await API.deletePhoto(photoId);
                showToast('图片已删除', 'success');
                await loadPhotos();
                updateAlbumTabs();
            } catch (e) {
                showToast('删除失败: ' + e.message, 'error');
            }
        }

        // ==================== 相册管理 ====================
        function openEditAlbumModal(album = null) {
            if (album) {
                $('#modalAlbumTitle').textContent = '✏️ 编辑相册';
                $('#editAlbumId').value = album.id;
                $('#albumName').value = album.name;
                $('#albumDesc').value = album.description || '';
                $('#modalAlbumDelete').style.display = '';
            } else {
                $('#modalAlbumTitle').textContent = '📁 新建相册';
                $('#editAlbumId').value = '';
                $('#albumName').value = '';
                $('#albumDesc').value = '';
                $('#modalAlbumDelete').style.display = 'none';
            }
            openModal(dom.modalAlbum);
            $('#albumName').focus();
        }

        async function saveAlbum() {
            const id = $('#editAlbumId').value;
            const name = $('#albumName').value.trim();
            const description = $('#albumDesc').value.trim();
            if (!name) { showToast('请输入相册名称', 'error');
                $('#albumName').focus(); return; }
            try {
                if (id) {
                    await API.updateAlbum(parseInt(id), { name, description });
                    showToast('相册已更新', 'success');
                } else {
                    await API.createAlbum({ name, description });
                    showToast('相册已创建', 'success');
                }
                closeModal(dom.modalAlbum);
                await loadAlbums();
                await loadPhotos();
            } catch (e) {
                showToast('操作失败: ' + e.message, 'error');
            }
        }

        async function deleteAlbumAction() {
            const id = parseInt($('#editAlbumId').value);
            if (!id) return;
            const album = STATE.albums.find(a => a.id === id);
            if (!confirm(`确定要删除相册「${album?.name || ''}」及其所有图片吗？此操作不可恢复！`)) return;
            try {
                await API.deleteAlbum(id);
                showToast('相册已删除', 'success');
                closeModal(dom.modalAlbum);
                if (STATE.currentAlbumId === String(id)) STATE.currentAlbumId = 'all';
                await loadAlbums();
                await loadPhotos();
            } catch (e) {
                showToast('删除失败: ' + e.message, 'error');
            }
        }

        // ==================== 图片添加 ====================
        function openAddPhotoModal() {
            if (!STATE.albums.length) {
                showToast('请先创建一个相册', 'info');
                openEditAlbumModal();
                return;
            }
            updatePhotoAlbumSelect();
            dom.photoTitle.value = '';
            dom.photoUrlInput.value = '';
            dom.uploadPreview.innerHTML = '';
            STATE.pendingFiles = [];
            dom.photoFileInput.value = '';
            openModal(dom.modalPhoto);
        }

        async function savePhoto() {
            const albumId = parseInt(dom.photoAlbumSelect.value);
            if (!albumId) { showToast('请选择相册', 'error'); return; }
            const title = dom.photoTitle.value.trim();
            const urlText = dom.photoUrlInput.value.trim();

            let addedCount = 0;
            const errors = [];

            // Handle file uploads
            if (STATE.pendingFiles.length > 0) {
                for (const file of STATE.pendingFiles) {
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('album_id', albumId);
                        formData.append('title', title || file.name.replace(/\.[^.]+$/, ''));
                        await API.createPhoto(formData);
                        addedCount++;
                    } catch (e) {
                        errors.push(`${file.name}: ${e.message}`);
                    }
                }
            }

            // Handle URL imports
            if (urlText) {
                const urls = urlText.split('\n').map(u => u.trim()).filter(u => u);
                for (const url of urls) {
                    try {
                        await API.createPhotoByUrl({
                            url,
                            album_id: albumId,
                            title: title || '',
                        });
                        addedCount++;
                    } catch (e) {
                        errors.push(`${url.substring(0, 40)}...: ${e.message}`);
                    }
                }
            }

            if (addedCount > 0) {
                showToast(`成功添加 ${addedCount} 张图片`, 'success');
                closeModal(dom.modalPhoto);
                await loadPhotos();
                updateAlbumTabs();
            } else if (errors.length > 0) {
                showToast('添加失败: ' + errors.join('; '), 'error');
            } else {
                showToast('请选择文件或输入图片URL', 'info');
            }
        }

        // ==================== 设置 ====================
        function openSettingsModal() {
            dom.settingStorageMode.value = STATE.storageMode;
            dom.settingSmmsToken.value = '';
            dom.settingNewPassword.value = '';
            updateSmmsTokenVisibility();
            openModal(dom.modalSettings);
        }

        async function saveSettings() {
            const data = {
                storage_mode: dom.settingStorageMode.value,
                smms_token: dom.settingSmmsToken.value || undefined,
                new_password: dom.settingNewPassword.value || undefined,
            };
            try {
                await API.updateSettings(data);
                STATE.storageMode = data.storage_mode;
                dom.storageModeLabel.textContent =
                    data.storage_mode === 'local' ? '本地存储' :
                    data.storage_mode === 'smms' ? 'SM.MS图床' : '仅URL模式';
                showToast('设置已保存', 'success');
                closeModal(dom.modalSettings);
                if (data.new_password) {
                    showToast('密码已修改，请重新登录', 'info');
                    logout();
                }
            } catch (e) {
                showToast('保存失败: ' + e.message, 'error');
            }
        }

        // ==================== 事件绑定 ====================
        // Manage button
        dom.btnManage.addEventListener('click', () => {
            openModal(dom.modalAuth);
            $('#authPassword').value = '';
            $('#authPassword').focus();
        });
        $('#modalAuthClose').addEventListener('click', () => closeModal(dom.modalAuth));
        $('#modalAuthCancel').addEventListener('click', () => closeModal(dom.modalAuth));
        $('#modalAuthConfirm').addEventListener('click', () => {
            handleAuth($('#authPassword').value);
        });
        $('#authPassword').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') handleAuth($('#authPassword').value);
        });

        // Add Album
        dom.btnAddAlbum.addEventListener('click', () => openEditAlbumModal());
        $('#modalAlbumClose').addEventListener('click', () => closeModal(dom.modalAlbum));
        $('#modalAlbumCancel').addEventListener('click', () => closeModal(dom.modalAlbum));
        $('#modalAlbumSave').addEventListener('click', saveAlbum);
        $('#modalAlbumDelete').addEventListener('click', deleteAlbumAction);

        // Add Photo
        dom.btnAddPhoto.addEventListener('click', openAddPhotoModal);
        $('#modalPhotoClose').addEventListener('click', () => closeModal(dom.modalPhoto));
        $('#modalPhotoCancel').addEventListener('click', () => closeModal(dom.modalPhoto));
        $('#modalPhotoSave').addEventListener('click', savePhoto);

        // Settings
        dom.btnSettings.addEventListener('click', openSettingsModal);
        $('#modalSettingsClose').addEventListener('click', () => closeModal(dom.modalSettings));
        $('#modalSettingsCancel').addEventListener('click', () => closeModal(dom.modalSettings));
        $('#modalSettingsSave').addEventListener('click', saveSettings);
        dom.settingStorageMode.addEventListener('change', updateSmmsTokenVisibility);

        // Logout
        dom.btnLogout.addEventListener('click', logout);

        // Upload zone
        dom.uploadZone.addEventListener('click', () => dom.photoFileInput.click());
        dom.uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dom.uploadZone.classList.add('drag-over');
        });
        dom.uploadZone.addEventListener('dragleave', () => {
            dom.uploadZone.classList.remove('drag-over');
        });
        dom.uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dom.uploadZone.classList.remove('drag-over');
            handleFiles(e.dataTransfer.files);
        });
        dom.photoFileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        function handleFiles(fileList) {
            const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
            const maxSize = 20 * 1024 * 1024; // 20MB
            for (const file of fileList) {
                if (!validTypes.includes(file.type)) {
                    showToast(`文件 ${file.name} 格式不支持`, 'error');
                    continue;
                }
                if (file.size > maxSize) {
                    showToast(`文件 ${file.name} 超过20MB限制`, 'error');
                    continue;
                }
                STATE.pendingFiles.push(file);
                // Preview
                const reader = new FileReader();
                reader.onload = (ev) => {
                    const img = document.createElement('img');
                    img.src = ev.target.result;
                    img.className = 'upload-preview-item';
                    dom.uploadPreview.appendChild(img);
                };
                reader.readAsDataURL(file);
            }
        }

        // Lightbox
        $('#lightboxClose').addEventListener('click', closeLightbox);
        $('#lightboxPrev').addEventListener('click', lightboxPrev);
        $('#lightboxNext').addEventListener('click', lightboxNext);
        dom.lightbox.addEventListener('click', (e) => {
            if (e.target === dom.lightbox) closeLightbox();
        });
        document.addEventListener('keydown', (e) => {
            if (!dom.lightbox.classList.contains('active')) return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowRight') lightboxNext();
            if (e.key === 'ArrowLeft') lightboxPrev();
        });
        // Touch swipe for lightbox
        let touchStartX = 0;
        dom.lightbox.addEventListener('touchstart', (e) => { touchStartX = e.touches[0].clientX; });
        dom.lightbox.addEventListener('touchend', (e) => {
            const diff = e.changedTouches[0].clientX - touchStartX;
            if (Math.abs(diff) > 60) {
                if (diff > 0) lightboxPrev();
                else lightboxNext();
            }
        });

        // Close modals on overlay click
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) closeModal(overlay);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal-overlay.active');
                if (activeModal) closeModal(activeModal);
            }
        });

        // ==================== 初始化 ====================
        async function init() {
            await checkAdmin();
            await loadAll();
            // If no albums and admin, auto-prompt
            if (STATE.isAdmin && STATE.albums.length === 0) {
                setTimeout(() => {
                    showToast('欢迎！请先创建一个相册来开始使用', 'info');
                }, 500);
            }
        }

        init();
    </script>
</body>
</html>

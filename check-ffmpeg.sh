#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  生成 FFmpeg 依赖检查脚本
# ═══════════════════════════════════════════════════════════════

# 检查 FFmpeg 是否安装
check_ffmpeg() {
    if ! command -v ffmpeg &> /dev/null; then
        echo "❌ FFmpeg 未安装"
        echo ""
        echo "📦 安装说明："
        echo "  • Debian/Ubuntu: sudo apt-get install ffmpeg"
        echo "  • macOS:         brew install ffmpeg"
        echo "  • CentOS/RHEL:   sudo yum install ffmpeg"
        echo "  • 其他:          https://ffmpeg.org/download.html"
        exit 1
    fi
    
    echo "✅ FFmpeg 已安装"
    ffmpeg -version | head -1
}

# 检查 FFprobe 是否安装
check_ffprobe() {
    if ! command -v ffprobe &> /dev/null; then
        echo "❌ FFprobe 未安装（通常与 FFmpeg 一起）"
        exit 1
    fi
    
    echo "✅ FFprobe 已安装"
    ffprobe -version | head -1
}

# 主函数
main() {
    echo "🔍 检查流媒体依赖..."
    echo ""
    
    check_ffmpeg
    echo ""
    check_ffprobe
    
    echo ""
    echo "✨ 所有依赖检查完成！可以安全使用在线播放功能。"
}

main

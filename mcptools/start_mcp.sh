#!/bin/bash
# MCP 服务启动脚本：start_mcp.sh
# ==============================
#
# 启动本地的 MCP 工具服务
#
# 使用方式：
#   bash start_mcp.sh [python_exec|web_search|all]
#
# 示例：
#   bash start_mcp.sh all     # 启动所有 MCP 服务
#   bash start_mcp.sh python_exec  # 只启动 Python 执行服务

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

start_python_exec() {
    echo "启动 Python 执行 MCP 服务..."
    python "$SCRIPT_DIR/python_exec_mcp.py"
}

start_web_search() {
    echo "启动 Web 搜索 MCP 服务..."
    python "$SCRIPT_DIR/web_search_mcp.py"
}

case "${1:-all}" in
    python_exec)
        start_python_exec
        ;;
    web_search)
        start_web_search
        ;;
    all)
        echo "启动所有 MCP 服务（按 Ctrl+C 停止）..."
        # 并行启动两个服务
        start_python_exec &
        start_web_search &
        wait
        ;;
    *)
        echo "用法: $0 [python_exec|web_search|all]"
        exit 1
        ;;
esac
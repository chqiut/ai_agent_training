#!/bin/bash
# 测试运行脚本：run_all.sh
# ======================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================"
echo "AI Agent Training - 运行所有测试"
echo "========================================"
echo ""

# 运行 pytest
python -m pytest tests/ -v --tb=short

echo ""
echo "========================================"
echo "测试完成！"
echo "========================================"
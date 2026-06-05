# -*- coding: utf-8 -*-
"""
测试环境初始化：_common.py
========================

提供测试所需的通用工具和设置。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup_test_env():
    """设置测试环境"""
    os.environ.setdefault("DEEPSEEK_API_KEY", "test_key_for_testing")


def get_test_data_path(filename: str) -> Path:
    """获取测试数据文件路径"""
    return PROJECT_ROOT / "data" / filename


def get_test_db_path() -> Path:
    """获取测试数据库路径"""
    return PROJECT_ROOT / "duckdb" / "agent.db"
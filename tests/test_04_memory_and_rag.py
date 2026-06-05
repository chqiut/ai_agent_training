# -*- coding: utf-8 -*-
"""
实验4测试：记忆系统与 RAG
========================

测试三层记忆系统和 RAG 检索：
- 短期记忆
- 中期记忆
- 长期记忆（RAG）
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env

setup_test_env()

from core.memory import (
    ShortTermMemory,
    MediumTermMemory,
    LongTermMemory,
    MemoryManager,
    MessageRecord
)
from core.rag import RAGRetriever


class TestShortTermMemory:
    """测试短期记忆"""

    def test_add_message(self):
        """测试添加消息"""
        memory = ShortTermMemory(window_size=5)

        memory.add_message("user", "你好")
        memory.add_message("assistant", "你好，我是 Agent")

        assert len(memory.messages) == 2

    def test_window_limit(self):
        """测试窗口限制"""
        memory = ShortTermMemory(window_size=3)

        for i in range(5):
            memory.add_message("user", f"消息{i}")

        assert len(memory.messages) == 3
        assert memory.messages[0].content == "消息2"

    def test_clear(self):
        """测试清空"""
        memory = ShortTermMemory()
        memory.add_message("user", "测试")
        memory.clear()

        assert len(memory.messages) == 0

    def test_to_messages(self):
        """测试转换为消息格式"""
        memory = ShortTermMemory()
        memory.add_message("user", "你好")

        messages = memory.to_messages()
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "你好"


class TestMediumTermMemory:
    """测试中期记忆"""

    def test_should_generate_summary(self):
        """测试是否需要生成摘要"""
        memory = MediumTermMemory(summary_trigger=5)

        assert memory.should_generate_summary(3) is False
        assert memory.should_generate_summary(5) is True
        assert memory.should_generate_summary(10) is True

    def test_get_summary(self):
        """测试获取摘要"""
        memory = MediumTermMemory()
        memory.current_summary = "测试摘要"

        assert memory.get_summary() == "测试摘要"


class TestLongTermMemory:
    """测试长期记忆"""

    def test_initialization(self):
        """测试初始化"""
        memory = LongTermMemory(index_path="nonexistent.faiss")
        result = memory.initialize()

        # 索引不存在时应该返回 False
        assert result is False


class TestMemoryManager:
    """测试记忆管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = MemoryManager()

        assert manager.short_term is not None
        assert manager.medium_term is not None
        assert manager.long_term is not None

    def test_add_message(self):
        """测试添加消息"""
        manager = MemoryManager()
        manager.add_message("user", "测试消息")

        assert len(manager.short_term.messages) == 1

    def test_should_summarize(self):
        """测试摘要检查"""
        manager = MemoryManager(
            short_term_window=20,
            medium_term_trigger=10
        )

        # 添加10 条消息
        for i in range(10):
            manager.add_message("user", f"消息{i}")

        assert manager.should_summarize() is True

    def test_get_context(self):
        """测试获取上下文"""
        manager = MemoryManager()
        manager.add_message("user", "测试")
        manager.add_message("assistant", "回复")

        context = manager.get_context()
        assert len(context) == 2


class TestRAGRetriever:
    """测试 RAG 检索器"""

    def test_retriever_initialization(self):
        """测试检索器初始化"""
        retriever = RAGRetriever(
            index_path="nonexistent.faiss",
            docs_path="nonexistent.pkl"
        )

        # 索引不存在时应该初始化失败
        result = retriever.initialize()
        assert result is False

    def test_retrieve_empty(self):
        """测试空检索"""
        retriever = RAGRetriever()
        results = retriever.retrieve("测试查询")

        # 索引不存在时应该返回空列表
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
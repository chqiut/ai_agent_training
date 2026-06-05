# -*- coding: utf-8 -*-
"""
三层记忆系统：memory.py
======================

本模块实现了 Agent 的三层记忆系统，模拟人类认知中的不同记忆类型。

三层记忆架构：
1. 短期记忆（Short-term Memory）
   - 模拟：工作记忆、当前对话
   - 实现：消息列表滚动窗口
   - 特点：信息立即可用，但容量有限

2. 中期记忆（Medium-term Memory）
   - 模拟：情景记忆、会话总结
   - 实现：LLM 生成摘要
   - 特点：压缩信息，保留关键点

3. 长期记忆（Long-term Memory）
   - 模拟：事实记忆、知识库
   - 实现：FAISS 向量数据库
   - 特点：持久化存储，支持语义检索

为什么需要三层记忆：
- 降低 LLM 的输入 token 成本
- 保持会话焦点，避免无关上下文干扰
- 积累知识，支持跨会话的信息利用

实验4内容：
    实现完整的三层记忆系统。
"""

from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

from .llm_client import LLMClient, Message


# =============================================================================
# 消息记录
# =============================================================================

@dataclass
class MessageRecord:
    """
    消息记录

    用于存储对话中的每条消息及其元数据。

    Attributes:
        role: 角色（system/user/assistant）
        content: 消息内容
        timestamp: 时间戳
        tool_calls: 工具调用记录（如果有）
        tool_results: 工具结果（如果有）
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: Optional[list[dict]] = None
    tool_results: Optional[list[dict]] = None


# =============================================================================
# 短期记忆
# =============================================================================

class ShortTermMemory:
    """
    短期记忆

    实现方式：消息列表滚动窗口

    设计思路：
    - 保存最近的 N 条对话消息
    - 每新来一条消息，就加入列表
    - 当列表超过窗口大小时，移除最老的消息
    - 保证 LLM 总是看到最新的上下文

    为什么叫"短期"：
    - 这些信息只在当前会话中有用
    - 会话结束后就会被丢弃
    - 不能积累跨会话的知识
    """

    def __init__(self, window_size: int = 20):
        """
        初始化短期记忆

        Args:
            window_size: 滚动窗口大小，默认保留最近 20 条消息
        """
        self.window_size = window_size
        self.messages: list[MessageRecord] = []

    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到短期记忆

        Args:
            role: 角色（user/assistant）
            content: 消息内容
        """
        record = MessageRecord(role=role, content=content)
        self.messages.append(record)

        # 滚动窗口：超过窗口大小时移除最老的消息
        if len(self.messages) > self.window_size:
            self.messages.pop(0)

    def add_tool_call(self, tool_name: str, arguments: dict, result: dict) -> None:
        """
        记录一次工具调用

        将工具调用和结果关联到最后一条用户消息上。
        这样可以保持对话的因果关联。

        Args:
            tool_name: 工具名称
            arguments: 工具参数
            result: 工具执行结果
        """
        if not self.messages:
            return

        # 获取最后一条用户消息
        last_user_msg = None
        for msg in reversed(self.messages):
            if msg.role == "user":
                last_user_msg = msg
                break

        if last_user_msg:
            if last_user_msg.tool_calls is None:
                last_user_msg.tool_calls = []
            last_user_msg.tool_calls.append({
                "tool": tool_name,
                "arguments": arguments,
                "result": result
            })

    def get_recent_messages(self, limit: int = 10) -> list[MessageRecord]:
        """
        获取最近的消息

        Args:
            limit: 返回消息数量限制

        Returns:
            最近的消息记录列表
        """
        return self.messages[-limit:]

    def get_all_messages(self) -> list[MessageRecord]:
        """获取所有消息"""
        return self.messages.copy()

    def clear(self) -> None:
        """清空短期记忆"""
        self.messages = []

    def to_messages(self) -> list[Message]:
        """
        转换为 LLM 的消息格式

        用于构建发送给 LLM 的对话历史。

        Returns:
            符合 LLM API 格式的消息列表
        """
        return [
            Message(msg.role, msg.content)
            for msg in self.messages
        ]


# =============================================================================
# 中期记忆
# =============================================================================

class MediumTermMemory:
    """
    中期记忆

    实现方式：LLM 生成会话摘要

    设计思路：
    - 当短期记忆超过一定阈值时（达到 N 条消息）
    - 让 LLM 生成一个会话摘要
    - 这个摘要保留了会话的关键信息
    - 后续对话可以用摘要替代原始消息

    为什么叫"中期"：
    - 比短期记忆更持久
    - 但仍然与当前会话主题相关
    - 不是长期积累的知识

    触发条件：
    - 当短期记忆消息数达到阈值时
    - 或者用户要求"总结一下之前的对话"
    """

    def __init__(self, summary_trigger: int = 10):
        """
        初始化中期记忆

        Args:
            summary_trigger: 触发摘要生成的消息数量阈值
        """
        self.summary_trigger = summary_trigger
        self.current_summary: Optional[str] = None
        self.last_summary_time: Optional[datetime] = None
        self.key_points: list[str] = []

    def should_generate_summary(self, short_term_count: int) -> bool:
        """
        检查是否需要生成摘要

        Args:
            short_term_count: 短期记忆的消息数量

        Returns:
            是否应该生成摘要
        """
        return short_term_count >= self.summary_trigger

    def generate_summary(
        self,
        messages: list[MessageRecord],
        llm_client: Optional[LLMClient] = None
    ) -> str:
        """
        生成会话摘要

       提示：摘要生成提示词的设计会影响摘要质量。
        我们要求摘要包含：关键问题、已完成的分析、结论。

        Args:
            messages: 短期记忆中的消息列表
            llm_client: 可选的 LLM 客户端，用于生成摘要

        Returns:
            生成的摘要文本
        """
        if not messages:
            return ""

        # 如果没有 LLM 客户端，返回简单拼接
        if llm_client is None:
            return f"会话包含 {len(messages)} 条消息"

        # 构建摘要生成提示
        messages_text = "\n".join([
            f"[{msg.role}]: {msg.content}"
            for msg in messages
        ])

        summary_prompt = f"""请总结以下对话的关键信息：

{messages_text}

请用简洁的语言总结：
1. 用户的主要问题或需求
2. 已完成的主要分析或操作
3. 得出的主要结论或答案

如果对话中没有实质性内容，请简短回复"无实质内容"。

摘要格式：
- 主要问题：...
- 已完成分析：...
- 结论：..."""

        try:
            response = llm_client.chat([
                Message("user", summary_prompt)
            ])
            self.current_summary = response.content
            self.last_summary_time = datetime.now()
            return response.content
        except Exception:
            return f"会话包含 {len(messages)} 条消息"

    def get_summary(self) -> Optional[str]:
        """获取当前摘要"""
        return self.current_summary

    def clear(self) -> None:
        """清空中期记忆"""
        self.current_summary = None
        self.last_summary_time = None
        self.key_points = []


# =============================================================================
# 长期记忆
# =============================================================================

class LongTermMemory:
    """
    长期记忆

    实现方式：FAISS 向量数据库

    设计思路：
    - 将重要的对话片段、事实、决策存储到向量数据库
    - 当需要时，通过语义检索找到相关的记忆
    - 这些记忆是跨会话持久化的

    为什么叫"长期"：
    - 存储在磁盘上，会话结束后不丢失
    - 可以积累大量历史信息
    - 通过向量相似度进行语义检索

    使用场景：
    - "之前关于 X 的讨论"
    - "上次做的 Y 分析"
    - "我记得 Z说过..."
    """

    def __init__(self, index_path: str):
        """
        初始化长期记忆

        Args:
            index_path: FAISS 索引路径
        """
        self.index_path = index_path
        self.index = None
        self.documents = []
        self._initialized = False

    def initialize(self) -> bool:
        """
        初始化 FAISS 索引

        尝试加载已有的索引。

        Returns:
            是否初始化成功
        """
        from pathlib import Path
        import faiss
        import pickle

        if self._initialized:
            return True

        index_file = Path(self.index_path)
        if not index_file.exists():
            return False

        try:
            docs_file = index_file.parent / "index.pkl"
            self.index = faiss.read_index(str(index_file))
            with open(docs_file, 'rb') as f:
                self.documents = pickle.load(f)
            self._initialized = True
            return True
        except Exception:
            return False

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """
        检索相关记忆

        Args:
            query: 检索查询
            top_k: 返回结果数量

        Returns:
            检索结果列表
        """
        from sentence_transformers import SentenceTransformer
        import numpy as np

        if not self._initialized:
            if not self.initialize():
                return []

        if not self.documents or self.index.ntotal == 0:
            return []

        try:
            model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            query_vector = model.encode([query])
            np.linalg.norm(query_vector, axis=1, keepdims=True)
            query_vector = query_vector / np.linalg.norm(query_vector, axis=1, keepdims=True)

            distances, indices = self.index.search(query_vector.astype('float32'), top_k)

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.documents):
                    doc = self.documents[idx]
                    results.append({
                        "content": doc.content,
                        "metadata": doc.metadata,
                        "score": float(dist)
                    })

            return results

        except Exception:
            return []

    def store(self, content: str, metadata: Optional[dict] = None) -> bool:
        """
        存储新记忆

        注意：这个功能需要索引支持增量添加。
        当前实现中，我们建议使用 build_index.py 预构建索引。

        Args:
            content: 记忆内容
            metadata: 元数据

        Returns:
            是否存储成功
        """
        #简化实现：长期记忆主要通过预构建的索引使用
        # 如需动态添加，需要实现增量索引
        return False

    def clear(self) -> None:
        """清空长期记忆（但不清除索引文件）"""
        self.documents = []


# =============================================================================
# 三层记忆管理器
# =============================================================================

class MemoryManager:
    """
    三层记忆管理器

    统一管理短期、中期、长期记忆。

    使用方式：
        manager = MemoryManager()
        manager.add_message("user", "我想分析销售数据")
        manager.add_message("assistant", "好的，请问您想分析哪个时间段？")

        # 获取完整上下文
        context = manager.get_context()
    """

    def __init__(
        self,
        short_term_window: int = 20,
        medium_term_trigger: int = 10,
        long_term_index_path: Optional[str] = None
    ):
        """
        初始化记忆管理器

        Args:
            short_term_window: 短期记忆窗口大小
            medium_term_trigger: 中期记忆触发阈值
            long_term_index_path: 长期记忆索引路径
        """
        self.short_term = ShortTermMemory(window_size=short_term_window)
        self.medium_term = MediumTermMemory(summary_trigger=medium_term_trigger)
        self.long_term = LongTermMemory(
            index_path=long_term_index_path or "faiss_index/index.faiss"
        )

        # 尝试初始化长期记忆
        self.long_term.initialize()

    def add_message(self, role: str, content: str) -> None:
        """添加消息到短期记忆"""
        self.short_term.add_message(role, content)

    def add_tool_call(self, tool_name: str, arguments: dict, result: dict) -> None:
        """记录工具调用"""
        self.short_term.add_tool_call(tool_name, arguments, result)

    def should_summarize(self) -> bool:
        """检查是否需要生成摘要"""
        return self.medium_term.should_generate_summary(
            len(self.short_term.messages)
        )

    def generate_summary(self, llm_client: Optional[LLMClient] = None) -> str:
        """生成会话摘要"""
        messages = self.short_term.get_all_messages()
        return self.medium_term.generate_summary(messages, llm_client)

    def retrieve_long_term(self, query: str, top_k: int = 3) -> list[dict]:
        """检索长期记忆"""
        return self.long_term.retrieve(query, top_k)

    def get_context(self) -> list[Message]:
        """
        获取完整的对话上下文

        构建发送给 LLM 的完整上下文，包含：
        1. 中期记忆的摘要（如果存在）
        2. 短期记忆的最近消息

        Returns:
            完整的消息列表
        """
        messages = []

        # 添加中期记忆摘要（如果有）
        summary = self.medium_term.get_summary()
        if summary:
            messages.append(Message(
                "system",
                f"【会话摘要】{summary}"
            ))

        # 添加短期记忆消息
        messages.extend(self.short_term.to_messages())

        return messages

    def clear_all(self) -> None:
        """清空所有记忆"""
        self.short_term.clear()
        self.medium_term.clear()
        self.long_term.clear()
# -*- coding: utf-8 -*-
"""
AI Agent Training - 核心模块
============================

本包包含 AI Agent 的核心组件：

- llm_client: LLM API 封装（支持 DeepSeek）
- prompts: System Prompt 模板
- tool_schemas: OpenAI 兼容的 Tool Schema 定义
- tools: Tool 注册与分发
- memory: 三层记忆系统
- rag: 向量检索增强生成
- agent_runtime: ReAct 主循环

教学重点：
    实验2: Function Calling（tool_schemas, tools）
    实验3: ReAct 循环（agent_runtime）
    实验4: 记忆系统（memory）
    实验5: RAG（rag）
"""

from .llm_client import LLMClient
from .agent_runtime import AgentRuntime

__all__ = [
    "LLMClient",
    "AgentRuntime",
]
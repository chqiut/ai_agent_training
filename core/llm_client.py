# -*- coding: utf-8 -*-
"""
LLM 客户端封装：llm_client.py
===========================

本模块负责与 LLM（大型语言模型）API 交互。

支持：
- DeepSeek（主要）
- OpenAI 兼容接口

核心功能：
1. 发送对话请求获取回复
2. 处理流式响应（可选）
3. 错误处理和重试机制

设计理念：
    将 LLM 视为一个"黑盒"，我们只关心输入和输出。
    输入是对话历史，输出是模型的回复文本。
"""

import os
import json
from typing import Optional, Iterator
from dataclasses import dataclass, field
import requests

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


@dataclass
class Message:
    """
    对话消息

    Attributes:
        role: 角色 - system（系统）, user（用户）, assistant（助手）, tool（工具结果）
        content: 消息内容
        tool_call_id: 工具调用ID（仅用于 tool 角色消息）
        tool_calls_json: 工具调用 JSON字符串（仅用于 assistant 角色消息）
    """
    role: str
    content: str
    tool_call_id: str = ""
    tool_calls_json: str = ""


@dataclass
class LLMResponse:
    """
    LLM 响应

    Attributes:
        content: 模型回复的文本内容
        raw_response: 原始 API 响应（用于调试）
        finish_reason: 停止原因（stop 或 length）
    """
    content: str
    raw_response: dict = field(default_factory=dict)
    finish_reason: str = "stop"


class LLMClient:
    """
    LLM 客户端

    封装与 LLM API 的交互，提供简洁的对话接口。

    使用示例：
        client = LLMClient()
        response = client.chat([Message("user", "你好")])
        print(response.content)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEEPSEEK_MODEL,
        api_url: str = DEEPSEEK_API_URL,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        初始化 LLM 客户端

        Args:
            api_key: API 密钥，如果为 None 则从环境变量 DEEPSEEK_API_KEY 读取
            model: 模型名称
            api_url: API 端点
            temperature: 采样温度（0-1），较低的值使输出更确定性
            max_tokens: 最大生成 token 数
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API密钥未提供，请设置 DEEPSEEK_API_KEY 环境变量，"
                "或直接在构造函数中传入 api_key 参数"
            )

        self.model = model
        self.api_url = api_url
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_headers(self) -> dict:
        """构建 HTTP 请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages: list[Message], tools: Optional[list] = None) -> dict:
        """
        构建请求载荷

        Args:
            messages: 对话历史
            tools: 可选的工具列表（用于 Function Calling）

        Returns:
            符合 OpenAI 兼容接口的请求体
        """
        messages_list = []
        for msg in messages:
            if msg.role == "tool":
                # Tool 消息需要包含 tool_call_id
                msg_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id
                }
                messages_list.append(msg_dict)
            elif msg.role == "assistant" and msg.tool_calls_json:
                # Assistant 消息如果包含 tool_calls_json，需要解析并包含 tool_calls
                assistant_dict = {
                    "role": msg.role,
                    "content": msg.content,
                }
                if msg.tool_calls_json:
                    assistant_dict["tool_calls"] = json.loads(msg.tool_calls_json)
                messages_list.append(assistant_dict)
            else:
                messages_list.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": messages_list,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # 如果提供了工具，添加 tools 和 tool_choice 参数
        # 这是启用 Function Calling 的关键
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        return payload

    def chat(
        self,
        messages: list[Message],
        tools: Optional[list] = None,
        stream: bool = False
    ) -> LLMResponse:
        """
        发送对话请求

        这是与 LLM 交互的核心方法。

        Args:
            messages: 对话历史列表
            tools: 可选的工具列表（用于 Function Calling）
            stream: 是否使用流式响应

        Returns:
            LLMResponse 对象，包含模型的回复

        流程说明：
            1. 将对话历史构建成请求格式
            2. 发送 HTTP POST 请求到 API
            3. 解析响应，提取文本内容
            4. 返回结构化的响应对象
        """
        headers = self._build_headers()
        payload = self._build_payload(messages, tools)

        try:
            # 发送请求到 LLM API
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120
            )

            # 检查 HTTP 状态码
            response.raise_for_status()

            # 解析 JSON 响应
            result = response.json()

            # 提取助手的回复
            # OpenAI 兼容格式：choices[0].message
            choice = result["choices"][0]
            assistant_message = choice["message"]

            # 提取回复内容
            content = assistant_message.get("content", "") or ""

            # 如果有工具调用，也一并返回
            # 这用于 Function Calling 场景
            tool_calls = assistant_message.get("tool_calls", [])

            # 构建响应对象
            llm_response = LLMResponse(
                content=content,
                raw_response=result,
                finish_reason=choice.get("finish_reason", "stop")
            )

            # 如果有工具调用，可以在 raw_response 中找到
            #后续 tools.py 模块会解析这些工具调用

            return llm_response

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM API 请求失败: {e}")

    def stream_chat(
        self,
        messages: list[Message],
        tools: Optional[list] = None
    ) -> Iterator[str]:
        """
        流式对话响应

        这是一个生成器函数，逐步返回模型的输出。
        适用于需要实时显示生成过程的场景。

        Args:
            messages: 对话历史
            tools: 可选的工具列表

        Yields:
            逐步生成的文本片段
        """
        headers = self._build_headers()
        payload = self._build_payload(messages, tools)
        payload["stream"] = True

        try:
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120,
                stream=True
            )
            response.raise_for_status()

            # 解析 SSE（Server-Sent Events）流
            for line in response.iter_lines():
                if line:
                    # SSE 格式：data: {...}
                    if line.startswith(b"data: "):
                        data = line[6:]
                        if data == b"[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM API 流式请求失败: {e}")


# 便捷函数：创建默认客户端
def create_default_client() -> LLMClient:
    """创建使用默认配置的 LLM 客户端"""
    return LLMClient(
        temperature=0.7,
        max_tokens=2048
    )
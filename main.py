# -*- coding: utf-8 -*-
"""
核心业务逻辑入口：main.py
========================

本模块是 AI Agent 的核心业务逻辑入口。

负责：
1. 初始化 AgentRuntime（ReAct 循环引擎）
2. 处理用户输入，调用 Agent
3. 返回结果和执行轨迹

被 app.py（FastAPI）调用。

使用方式：
    from main import process
    result = process("分析本月销售额最高的产品")
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

from typing import Optional
from dataclasses import dataclass

from core.agent_runtime import AgentRuntime, ReActTrace
from core.llm_client import LLMClient
from core.utils import get_logger

logger = get_logger("main")


@dataclass
class ProcessResult:
    """
    处理结果

    Attributes:
        response: Agent 的最终回复
        trace: 执行轨迹
        conversation_id: 会话 ID
    """
    response: str
    trace: ReActTrace
    conversation_id: Optional[str] = None


def create_agent() -> AgentRuntime:
    """
    创建 Agent 运行时实例

    Returns:
        配置好的 AgentRuntime 实例
    """
    llm_client = LLMClient(
        temperature=0.7,
        max_tokens=2048
    )

    agent = AgentRuntime(
        llm_client=llm_client,
        max_steps=10,
        enable_trace=True
    )

    return agent


def process(
    user_input: str,
    conversation_id: Optional[str] = None
) -> ProcessResult:
    """
    处理用户输入

    这是被 Web API（app.py）调用的主要入口函数。

    流程：
    1. 创建/获取 Agent 实例（如果有 conversation_id）
    2. 调用 ReAct 循环执行
    3. 返回结果和轨迹

    Args:
        user_input: 用户输入的问题
        conversation_id: 会话 ID（用于多轮对话）

    Returns:
        ProcessResult 对象
    """
    # 创建 Agent
    agent = create_agent()

    # 执行 ReAct 循环
    response, trace = agent.run(user_input)

    return ProcessResult(
        response=response,
        trace=trace,
        conversation_id=conversation_id
    )


def process_stream(user_input: str):
    """
    流式处理用户输入

    Args:
        user_input: 用户输入

    Yields:
        事件字典
    """
    agent = create_agent()

    for event in agent.run_stream(user_input):
        yield event


# 便捷函数
def quick_query(sql: str) -> dict:
    """
    快速执行 SQL 查询（不经过 ReAct 循环）

    用于简单的、直接的查询场景。

    Args:
        sql: SQL 查询语句

    Returns:
        查询结果
    """
    from core.tools import duckdb_query

    return duckdb_query(sql)


def main():
    """命令行交互入口"""
    print("=" * 60)
    print("AI Agent Training - 核心业务逻辑")
    print("=" * 60)
    print()
    print("输入您的问题，按 Enter 发送，输入 'quit' 退出")
    print()

    agent = create_agent()

    while True:
        try:
            user_input = input("用户: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见！")
                break

            print()
            print("Agent思考中...")
            print("-" * 40)

            response, trace = agent.run(user_input)

            print()
            print(f"Agent: {response}")
            print()
            print("-" * 40)
            print(f"执行步数: {trace.total_steps}")

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            logger.error(f"执行出错: {e}")
            print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
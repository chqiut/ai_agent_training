# -*- coding: utf-8 -*-
"""
ReAct 主循环：agent_runtime.py
=============================

本模块是 AI Agent 的核心——ReAct（Reason + Act）循环引擎。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎓 教学重点：这个文件是整个项目的教学核心！

在深入代码之前，请先理解 ReAct 架构的设计理念：

什么是 ReAct：
    ReAct = Reason（思考）+ Act（行动）+ Observe（观察）
    它是一种让 LLM 能够进行多步推理和工具使用的架构。

为什么需要 ReAct：
    1. LLM 本身不能执行操作（如查询数据库、搜索网页）
    2. LLM 需要能够调用工具来完成具体任务
    3. LLM 需要基于工具结果进行下一步推理
    4. 这形成了一个"思考-行动-观察"的循环

ReAct vs 普通 LLM：
    普通 LLM：用户问什么，直接回答（无法访问外部数据/工具）
    ReAct LLM：用户问什么 → 思考是否需要工具 → 调用工具 → 观察结果 → 回答

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

实验3内容：
    实现完整的 ReAct 循环，包括：
    - Reason：LLM 生成思考过程
    - Act：LLM 决定调用工具
    - Observe：获取工具结果并反馈给 LLM
    - 循环终止条件：达到 max_steps 或 LLM 认为完成
"""

import os
import json
from typing import Optional, Iterator, Any
from dataclasses import dataclass, field

from .llm_client import LLMClient, Message, LLMResponse
from .prompts import build_system_prompt
from .tool_schemas import ALL_TOOL_SCHEMAS
from .tools import ToolDispatcher
from .memory import MemoryManager


# =============================================================================
# ReAct 循环状态
# =============================================================================

@dataclass
class ReActStep:
    """
    ReAct 循环的单个步骤

    记录每一步的：思考、工具调用、工具结果。

    Attributes:
        step_number: 步骤编号
        thought: 思考过程（Reason阶段）
        tool_calls: 工具调用列表（Act 阶段）
        tool_results: 工具执行结果（Observe 阶段）
        final_response: 最终回复（如果 LLM 认为完成）
    """
    step_number: int
    thought: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    final_response: Optional[str] = None


@dataclass
class ReActTrace:
    """
    ReAct 执行轨迹

    记录整个 ReAct 循环的执行过程，用于调试和展示。

    Attributes:
        steps: 所有步骤列表
        total_steps: 总步骤数
        completed: 是否正常完成
        error: 错误信息（如果有）
    """
    steps: list[ReActStep] = field(default_factory=list)
    total_steps: int = 0
    completed: bool = False
    error: Optional[str] = None


# =============================================================================
# ReAct Agent 运行时
# =============================================================================

class AgentRuntime:
    """
    ReAct Agent 运行时

    这是 ReAct 循环的核心执行器。

   ┌─────────────────────────────────────────────────────────────────────────┐
    │ ReAct 循环流程图                                │
    │                                                                          │
    │     ┌──────────────┐                                                   │
    │     │  用户输入 │                                                   │
    │     └──────┬───────┘                                                   │
    │            │                                                            │
    │            ▼                                                            │
    │     ┌──────────────┐                                                   │
    │     │   开始循环    │                                                   │
    │     └──────┬───────┘                                                   │
    │            │                                                            │
    │            ▼                                                            │
    │     ┌──────────────────────────────────────────────┐                   │
    │     │  步骤1-∞: ReAct 单步循环                     │                   │
    │     │                                              │                   │
    │     │  ┌────────────────────────────────────────┐  │                   │
    │     │  │ 【Reason】LLM 生成思考                  │  │                   │
    │     │  │  - 分析当前状态                          │  │                   │
    │     │  │  - 决定是否需要工具                      │  │                   │
    │     │  │  - 如果需要，选择工具并生成参数           │  │                   │
    │     │  └────────────────────────────────────────┘  │                   │
    │     │              │                                │                   │
    │     │              ▼                                │                   │
    │     │  ┌────────────────────────────────────────┐  │                   │
    │     │  │ 【Act】执行工具或生成回复                │  │                   │
    │     │  │  - 如果有工具调用，执行工具 │  │                   │
    │     │  │  - 如果没有工具调用，说明任务完成 │  │                   │
    │     │  └────────────────────────────────────────┘  │                   │
    │     │              │                                │                   │
    │     │              ▼                                │                   │
    │     │  ┌────────────────────────────────────────┐  │                   │
    │     │  │ 【Observe】观察结果                      │  │                   │
    │     │  │  - 收集工具执行结果                      │  │                   │
    │     │  │  - 将结果加入对话历史 │  │                   │
    │     │  │  - 准备下一次循环 │  │                   │
    │     │  └────────────────────────────────────────┘  │                   │
    │     │              │                                │                   │
    │     │              ▼ │                   │
    │     │     ┌─────────────────┐                      │                   │
    │     │     │ 检查终止条件   │                      │                   │
    │     │     └────────┬────────┘                      │                   │
    │     │              │                               │                   │
    │     │    ┌────────┴────────┐                      │                   │
    │     │     ▼                 ▼                      │                   │
    │     │  继续循环 结束循环                     │                   │
    │     └──────────────────────────────────────────────┘                   │
    │            │                                                            │
    │            ▼                                                            │
    │     ┌──────────────┐                                                   │
    │     │  返回结果    │                                                   │
    │     └──────────────┘                                                   │
    └─────────────────────────────────────────────────────────────────────────┘

    使用示例：
        runtime = AgentRuntime()
        result = runtime.run("分析本月销售额最高的产品")

        # 获取执行轨迹
        for step in result.steps:
            print(f"步骤 {step.step_number}: {step.thought}")
            if step.tool_calls:
                print(f"  工具调用: {step.tool_calls}")
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_steps: int = 10,
        enable_trace: bool = True
    ):
        """
        初始化 Agent运行时

        Args:
            llm_client: LLM 客户端（如果为 None，使用默认配置）
            max_steps: 最大循环步数，防止无限循环
            enable_trace: 是否记录执行轨迹
        """
        # LLM 客户端
        # ─────────────────────────────────────────────────────────────────────────
        # 我们使用 LLM 来进行推理和决策。
        # LLM 就像 Agent 的"大脑"，负责：
        # 1.理解用户的问题
        # 2. 生成思考过程
        # 3. 决定是否需要调用工具
        # 4. 如果需要，选择哪个工具并生成参数
        self.llm_client = llm_client or self._create_default_llm_client()

        # 工具分发器
        # ─────────────────────────────────────────────────────────────────────────
        # 工具分发器负责根据 LLM 的决策执行具体的工具。
        # 它就像 Agent 的"手"，能够：
        # 1. 执行 SQL 查询（DuckDB）
        # 2.搜索网页（DuckDuckGo）
        # 3. 运行 Python 代码
        # 4. 检索向量数据库（RAG）
        self.dispatcher = ToolDispatcher()

        # 记忆管理器
        # ─────────────────────────────────────────────────────────────────────────
        # 记忆管理器实现了三层记忆系统：
        # 1. 短期记忆：保存最近的对话
        # 2. 中期记忆：保存会话摘要
        # 3. 长期记忆：通过 RAG 检索历史知识
        self.memory = MemoryManager()

        # 配置
        # ─────────────────────────────────────────────────────────────────────────
        # max_steps 是一个重要的安全机制。
        # 理论上 ReAct 循环可以无限进行（LLM 一直调用工具），
        # 但这可能导致：
        # 1. 无限循环（工具返回的结果导致 LLM 再次调用同一工具）
        # 2.  Token 消耗过大
        # 3. 用户等待时间过长
        # 所以我们设置 max_steps 来限制循环次数。
        self.max_steps = max_steps

        # 是否记录执行轨迹
        # ─────────────────────────────────────────────────────────────────────────
        # 执行轨迹（Trace）记录了 ReAct 循环的每一步。
        # 这对于调试和教学非常有价值：
        # 1. 调试：可以看到 LLM 的思考过程是否正确
        # 2. 教学：学生可以看到 Agent 是如何一步步解决问题的
        # 3. 信任：用户可以看到 Agent 为什么做出某个决定
        self.enable_trace = enable_trace
        self.trace = ReActTrace()

        # System Prompt
        # ─────────────────────────────────────────────────────────────────────────
        # System Prompt 是给 LLM 的指令，决定了 Agent 的行为模式。
        # 它告诉 LLM：
        # 1. 你的角色是什么（智能数据分析助手）
        # 2. 你有哪些能力（可以使用哪些工具）
        # 3. 你应该如何思考（ReAct 架构）
        #
        # System Prompt 的设计直接影响 Agent 的表现。
        # 一个好的 System Prompt 应该：
        # 1. 清晰明确，不容易产生歧义
        # 2. 结构化组织，便于 LLM 理解
        # 3. 提供足够的上下文，但不过于冗长
        self.system_prompt = build_system_prompt(ALL_TOOL_SCHEMAS)

    def _create_default_llm_client(self) -> LLMClient:
        """创建默认的 LLM 客户端"""
        return LLMClient(
            temperature=0.7,
            max_tokens=2048
        )

    # =========================================================================
    # 核心方法：ReAct 循环
    # =========================================================================

    def run(self, user_input: str) -> tuple[str, ReActTrace]:
        """
        执行 ReAct 循环

        这是 AgentRuntime 的核心方法，实现了完整的 ReAct 循环。

        流程：
        1. 初始化：将用户输入加入记忆
        2. 循环执行：Reason → Act → Observe
        3. 终止：达到 max_steps 或 LLM 生成最终回复
        4. 返回：最终回复和执行轨迹

        Args:
            user_input: 用户输入的问题或指令

        Returns:
            (最终回复, 执行轨迹)
        """
        # 初始化
        # ─────────────────────────────────────────────────────────────────────────
        # 在开始 ReAct 循环之前，我们需要做一些初始化工作：
        # 1. 清空上一轮的轨迹记录
        # 2. 将用户输入加入短期记忆
        # 3. 构建初始的对话历史
        self.trace = ReActTrace()
        self.memory.add_message("user", user_input)

        # 构建初始消息列表
        # 注意：这里我们使用完整的系统提示词作为 system消息
        messages = [
            Message("system", self.system_prompt),
        ]

        # 添加记忆中的历史消息（如果有摘要，会包含摘要）
        messages.extend(self.memory.get_context())

        # ReAct 循环
        # ─────────────────────────────────────────────────────────────────────────
        #
        # 这里是 ReAct 的核心——一个 while 循环，不断执行：
        # Reason → Act → Observe
        #
        # 每次循环包含三个阶段：
        #
        # 【阶段1：Reason（思考）】
        #   LLM 分析当前状态：
        #   - 用户想要什么？
        #   - 我已经知道了什么？
        #   - 需要调用工具吗？
        #   - 如果需要，哪个工具？参数是什么？
        #
        # 【阶段2：Act（行动）】
        #   如果 LLM 决定调用工具，执行工具并获取结果
        #   如果 LLM 认为任务完成，生成最终回复并退出循环
        #
        # 【阶段3：Observe（观察）】
        #   将工具执行结果加入对话历史
        #   准备进入下一次循环
        #
        step_count = 0
        final_response = ""

        while step_count < self.max_steps:
            step_count += 1
            current_step = ReActStep(step_number=step_count)

            # ┌─────────────────────────────────────────────────────────────────────┐
            # │ 【Reason】LLM 生成思考和决策                                        │
            # └─────────────────────────────────────────────────────────────────────┘

            # 调用 LLM，获取响应
            # 关键点：我们将 tools 传递给 LLM，让它知道有哪些工具可用
            # LLM 会根据情况决定：
            # 1. 直接回复（任务完成，不需要工具）
            # 2. 调用工具（需要工具协助）
            #
            # 返回的 assistant_message 包含：
            # - content: LLM 的文本回复（可能是思考过程）
            # - tool_calls: LLM 决定调用的工具列表
            llm_response = self.llm_client.chat(messages, tools=ALL_TOOL_SCHEMAS)
            assistant_message = llm_response.raw_response["choices"][0]["message"]

            # 记录本次 LLM 调用的 token 使用情况
            last_usage = llm_response.usage

            # 提取 LLM 的思考过程
            # 注意：LLM 可能会在 content 中写出它的思考过程
            # 这个思考过程对于调试和教学非常重要
            current_step.thought = assistant_message.get("content", "")

            # ┌─────────────────────────────────────────────────────────────────────┐
            # │ 【Act】执行工具或生成回复 │
            # └─────────────────────────────────────────────────────────────────────┘

            # 检查是否有工具调用
            tool_calls = assistant_message.get("tool_calls", [])

            if not tool_calls:
                # 没有工具调用，说明 LLM 认为任务完成了
                # content 就是 LLM 的最终回复
                #
                # 为什么没有工具调用就算完成？
                # 因为我们的 System Prompt 告诉 LLM：
                # "如果你已经知道答案，就直接回复用户"
                # "只有在需要使用工具时，才调用工具"
                #
                # 所以没有 tool_calls 意味着 LLM 认为：
                # 1. 问题可以直接回答，不需要工具
                # 2. 或者工具执行后已经得到了足够的信息
                final_response = assistant_message.get("content", "") or "已完成"
                current_step.final_response = final_response
                break

            # 有工具调用，执行工具
            # ─────────────────────────────────────────────────────────────────────
            #
            # 当 LLM 决定调用工具时，我们：
            # 1. 解析 tool_calls（工具名称和参数）
            # 2. 使用 dispatcher 执行工具
            # 3.收集执行结果
            # 4. 将结果格式化为消息，加入对话历史
            #
            # 关键点：工具执行的结果会作为 "tool" 角色消息加入对话
            # 这样 LLM 在下一轮就能"看到"工具返回的结果

            # 记录工具调用
            current_step.tool_calls = tool_calls

            # 执行工具并获取结果
            tool_results = self.dispatcher.dispatch_from_llm_response(assistant_message)
            current_step.tool_results = tool_results

            # ┌─────────────────────────────────────────────────────────────────────┐
            # │ 【Observe】处理工具执行结果                                          │
            # └─────────────────────────────────────────────────────────────────────┘

            # 将工具调用和结果格式化为消息，加入对话历史
            # ─────────────────────────────────────────────────────────────────────
            #
            # 在 ReAct 架构中，工具结果是通过"观察"机制传递给 LLM 的。
            # 具体实现是：
            # 1. 工具执行后，我们得到结果
            # 2. 将结果格式化为 role="tool" 的消息
            # 3. 每条工具消息关联一个 tool_call_id
            # 4. 将这些消息加入对话历史
            # 5. LLM 在下一轮循环中会"看到"这些结果
            #
            # 这就是为什么 ReAct 循环能够工作：
            # -每次循环都会更新对话历史
            # - 新增的 tool消息就是"观察"到的结果
            # - LLM 基于新的观察结果进行下一轮推理
            #

            # 首先添加助手消息（包含 tool_calls）
            assistant_content = assistant_message.get("content", "") or ""
            messages.append(Message(
                "assistant",
                assistant_content,
                tool_calls_json=json.dumps(assistant_message.get("tool_calls", []))
            ))

            # 然后添加工具结果消息
            for call, result in zip(tool_calls, tool_results):
                # LLM 生成的工具调用
                tool_name = call["function"]["name"]
                call_id = call.get("id", "")

                # 工具执行结果
                # 我们将结果格式化为字符串，方便 LLM 理解
                if result.get("success"):
                    #成功：将结果转换为 JSON 字符串
                    result_content = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    # 失败：返回错误信息，并提示可以尝试其他工具
                    error_msg = result.get('error', '未知错误')
                    suggestion = ""

                    # 针对搜索类工具，提示可以尝试 python_exec
                    if 'search' in tool_name.lower() or 'web' in tool_name.lower():
                        suggestion = "\n\n提示：该工具执行失败，可以尝试使用 python_exec 工具获取网络信息。"
                    # 针对 python_exec 失败，提示可以尝试搜索
                    elif 'python' in tool_name.lower():
                        suggestion = "\n\n提示：该工具执行失败，可以尝试使用 web_search 工具搜索网络信息。"

                    result_content = f"错误: {error_msg}{suggestion}"

                # 加入对话历史
                # 角色是 "tool"，表示这是工具执行的结果
                # tool_call_id 用于关联 tool_calls
                messages.append(Message(
                    "tool",
                    result_content,
                    tool_call_id=call_id
                ))

                # 记录到记忆系统（用于后续分析）
                self.memory.add_tool_call(
                    tool_name,
                    call["function"].get("arguments", {}),
                    result
                )

            # 这一轮结束，记录步骤
            if self.enable_trace:
                self.trace.steps.append(current_step)

        # 循环结束（正常完成或达到 max_steps）
        # ─────────────────────────────────────────────────────────────────────────
        #
        # ReAct 循环可能因为以下原因结束：
        # 1. LLM 生成了最终回复（没有更多工具调用）← 正常结束
        # 2. 达到 max_steps 限制 ← 安全终止
        #
        # 无论哪种方式，我们都：
        # 1. 将 LLM 的最终回复加入记忆
        # 2. 更新轨迹状态
        # 3. 返回结果

        if step_count >= self.max_steps and not final_response:
            # 达到最大步数但没有回复，说明循环没有正常结束
            #尝试再做一次 LLM 调用，基于已收集的工具结果生成回复
            try:
                llm_response = self.llm_client.chat(messages, tools=ALL_TOOL_SCHEMAS)
                assistant_message = llm_response.raw_response["choices"][0]["message"]
                last_usage = llm_response.usage

                # 检查是否生成了回复
                tool_calls = assistant_message.get("tool_calls", [])
                if not tool_calls:
                    final_response = assistant_message.get("content", "") or "已完成"
                else:
                    #仍然有工具调用，说明无法完成
                    final_response = (
                        f"已达到最大步数限制（{self.max_steps}步），"
                        "任务可能未完成。请尝试简化您的问题。"
                    )
                    self.trace.error = "达到最大步数限制"
            except Exception as e:
                final_response = (
                    f"已达到最大步数限制（{self.max_steps}步），"
                    f"生成回复时出错：{str(e)}"
                )
                self.trace.error = "达到最大步数限制并发生错误"

        # 将最终回复加入记忆
        self.memory.add_message("assistant", final_response)

        # 更新轨迹
        self.trace.total_steps = step_count
        self.trace.completed = bool(final_response)

        return final_response, self.trace, last_usage

    def run_stream(self, user_input: str) -> Iterator[dict]:
        """
        流式执行 ReAct 循环

        这是一个生成器版本，逐步返回执行过程中的事件。

        用于需要实时显示执行过程的场景（如 Web 界面）。

        Yields:
            事件字典，包含：
            - type: 事件类型（thought/tool_call/result/final）
            - content: 事件内容
            - step: 当前步骤编号
        """
        self.trace = ReActTrace()
        self.memory.add_message("user", user_input)

        messages = [
            Message("system", self.system_prompt),
        ]
        messages.extend(self.memory.get_context())

        step_count = 0

        while step_count < self.max_steps:
            step_count += 1

            yield {
                "type": "step_start",
                "step": step_count,
                "content": f"开始步骤 {step_count}"
            }

            # Reason
            llm_response = self.llm_client.chat(messages, tools=ALL_TOOL_SCHEMAS)
            assistant_message = llm_response.raw_response["choices"][0]["message"]

            thought = assistant_message.get("content", "")
            if thought:
                yield {
                    "type": "thought",
                    "step": step_count,
                    "content": thought
                }

            tool_calls = assistant_message.get("tool_calls", [])

            if not tool_calls:
                # Decision: Agent 决定不再调用工具，直接生成最终回答
                # 从 LLM 的 thought 中提取关键信息，构建决策理由
                thought_preview = thought[:300] + "..." if len(thought) > 300 else thought

                # 分析已收集的工具结果，检查数据完整性
                collected_data_info = self._summarize_collected_data()

                decision_text = (
                    f"LLM 决定停止工具调用。\n"
                    f"已收集数据：{collected_data_info}\n"
                    f"思考过程：{thought_preview}\n"
                    f"→ 生成最终回答"
                )
                yield {
                    "type": "decision",
                    "step": step_count,
                    "content": decision_text
                }
                final_response = thought or "已完成"
                yield {
                    "type": "final",
                    "step": step_count,
                    "content": final_response
                }
                break

            # Act
            for call in tool_calls:
                tool_name = call["function"]["name"]
                yield {
                    "type": "tool_call",
                    "step": step_count,
                    "content": f"调用工具: {tool_name}"
                }

            # Observe
            tool_results = self.dispatcher.dispatch_from_llm_response(assistant_message)

            # 首先添加助手消息（包含 tool_calls）
            messages.append(Message(
                "assistant",
                assistant_message.get("content", "") or "",
                tool_calls_json=json.dumps(tool_calls)
            ))

            for call, result in zip(tool_calls, tool_results):
                tool_name = call["function"]["name"]
                call_id = call.get("id", "")

                if result.get("success"):
                    result_text = json.dumps(result, ensure_ascii=False, indent=2)
                else:
                    error_msg = result.get('error', '未知错误')
                    suggestion = ""

                    if 'search' in tool_name.lower() or 'web' in tool_name.lower():
                        suggestion = "\n\n提示：该工具执行失败，可以尝试使用 python_exec 工具获取网络信息。"
                    elif 'python' in tool_name.lower():
                        suggestion = "\n\n提示：该工具执行失败，可以尝试使用 web_search 工具搜索网络信息。"

                    result_text = f"错误: {error_msg}{suggestion}"

                messages.append(Message(
                    "tool",
                    f"[{tool_name}]\n{result_text}",
                    tool_call_id=call_id
                ))

                self.memory.add_tool_call(
                    tool_name,
                    call["function"].get("arguments", {}),
                    result
                )

                yield {
                    "type": "tool_result",
                    "step": step_count,
                    "tool": tool_name,
                    "content": result_text[:500]  # 截断过长结果
                }

        # 达到 max_steps 限制，强制终止
        if step_count >= self.max_steps:
            yield {
                "type": "decision",
                "step": step_count,
                "content": f"⚠️ 达到最大步数限制（{self.max_steps}步），强制终止循环。请简化问题或增加 max_steps。"
            }
            yield {
                "type": "final",
                "step": step_count,
                "content": f"已达到最大步数限制（{self.max_steps}步），任务可能未完成。请尝试简化您的问题。"
            }

        self.trace.total_steps = step_count
        self.trace.completed = True

    def _summarize_collected_data(self) -> str:
        """
        总结已收集的数据，检测数据完整性
        用于在 Decision 中向用户展示已收集了哪些数据
        """
        summaries = []

        # 遍历 short_term 中的消息记录，获取 tool_calls
        for msg in self.memory.short_term.messages:
            tool_calls = getattr(msg, 'tool_calls', None)
            if not tool_calls:
                continue
            for call in tool_calls:
                tool_name = call.get("tool", "")
                result = call.get("result", {})
                if result.get("success"):
                    row_count = result.get("row_count", 0)
                    columns = result.get("columns", [])
                    columns_str = ", ".join(columns[:5])  # 只显示前5列
                    if len(columns) > 5:
                        columns_str += "..."

                    # 检测关键维度是否存在
                    key_dims = []
                    for col in columns:
                        col_lower = col.lower()
                        if any(k in col_lower for k in ["区域", "region"]):
                            key_dims.append("区域")
                        if any(k in col_lower for k in ["产品", "product", "商品", "item"]):
                            key_dims.append("产品")
                        if any(k in col_lower for k in ["月份", "month", "时间"]):
                            key_dims.append("时间")

                    dims_str = "/".join(set(key_dims)) if key_dims else "通用"

                    summaries.append(
                        f"{tool_name}({row_count}行, [{dims_str}])"
                    )
                else:
                    summaries.append(f"{tool_name}(失败)")

        if not summaries:
            return "无工具调用记录"

        return " | ".join(summaries)

    def clear(self) -> None:
        """清空当前会话状态"""
        self.trace = ReActTrace()
        self.memory.clear_all()
# -*- coding: utf-8 -*-
"""
实验3测试：ReAct 循环
===================

测试 ReAct 循环的实现：
- 思考-行动-观察循环
- 工具调用
- 最大步数限制
- 执行轨迹记录
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env

setup_test_env()

from core.agent_runtime import AgentRuntime, ReActStep, ReActTrace
from core.llm_client import LLMClient, Message


class TestReActStep:
    """测试 ReAct 步骤"""

    def test_step_creation(self):
        """测试步骤创建"""
        step = ReActStep(step_number=1)
        assert step.step_number == 1
        assert step.thought == ""
        assert step.tool_calls == []
        assert step.tool_results == []


class TestReActTrace:
    """测试执行轨迹"""

    def test_trace_creation(self):
        """测试轨迹创建"""
        trace = ReActTrace()
        assert trace.steps == []
        assert trace.total_steps == 0
        assert trace.completed is False
        assert trace.error is None

    def test_trace_with_steps(self):
        """测试带步骤的轨迹"""
        trace = ReActTrace()
        step1 = ReActStep(step_number=1, thought="测试思考")
        trace.steps.append(step1)
        trace.total_steps = 1

        assert len(trace.steps) == 1
        assert trace.total_steps == 1


class TestAgentRuntime:
    """测试 Agent 运行时"""

    def test_runtime_initialization(self):
        """测试运行时初始化"""
        runtime = AgentRuntime(max_steps=5)

        assert runtime.max_steps == 5
        assert runtime.enable_trace is True
        assert runtime.trace is not None

    def test_runtime_with_mock_llm(self):
        """测试运行时（使用 Mock LLM）"""
        # 这个测试需要 Mock LLM 客户端
        #实际测试中应该使用 unittest.mock

        class MockLLMClient:
            def chat(self, messages, tools=None):
                class MockResponse:
                    raw_response = {
                        "choices": [{
                            "message": {
                                "content": "测试回复",
                                "tool_calls": []
                            }
                        }]
                    }
                return MockResponse()

        runtime = AgentRuntime(llm_client=MockLLMClient())
        result, trace = runtime.run("测试输入")

        assert result == "测试回复"
        assert trace is not None

    def test_max_steps_protection(self):
        """测试最大步数保护"""

        class InfiniteLoopLLM:
            """模拟无限循环的 LLM"""
            def chat(self, messages, tools=None):
                class MockResponse:
                    raw_response = {
                        "choices": [{
                            "message": {
                                "content": "",
                                "tool_calls": [{
                                    "id": "call_1",
                                    "function": {
                                        "name": "duckdb_query",
                                        "arguments": "{}"
                                    }
                                }]
                            }
                        }]
                    }
                return MockResponse()

        runtime = AgentRuntime(llm_client=InfiniteLoopLLM(), max_steps=3)
        result, trace = runtime.run("测试")

        # 应该达到最大步数限制
        assert trace.total_steps == 3


class TestReActFlow:
    """测试 ReAct 流程"""

    def test_flow_without_tools(self):
        """测试不需要工具的流程"""
        # 当 LLM 不生成 tool_calls 时，应该直接返回回复

        class DirectResponseLLM:
            def chat(self, messages, tools=None):
                class MockResponse:
                    raw_response = {
                        "choices": [{
                            "message": {
                                "content": "直接回答",
                                "tool_calls": []
                            }
                        }]
                    }
                return MockResponse()

        runtime = AgentRuntime(llm_client=DirectResponseLLM())
        result, trace = runtime.run("你好")

        assert result == "直接回答"
        assert trace.completed is True

    def test_flow_with_tools(self):
        """测试需要工具的流程"""

        class ToolCallingLLM:
            call_count = 0

            def chat(self, messages, tools=None):
                ToolCallingLLM.call_count += 1

                if ToolCallingLLM.call_count == 1:
                    # 第一次调用：需要工具
                    class MockResponse:
                        raw_response = {
                            "choices": [{
                                "message": {
                                    "content": "我需要查询数据库",
                                    "tool_calls": [{
                                        "id": "call_1",
                                        "function": {
                                            "name": "duckdb_query",
                                            "arguments": '{"sql": "SELECT 1"}'
                                        }
                                    }]
                                }
                            }]
                        }
                    return MockResponse()
                else:
                    # 第二次调用：完成
                    class MockResponse:
                        raw_response = {
                            "choices": [{
                                "message": {
                                    "content": "查询结果是1",
                                    "tool_calls": []
                                }
                            }]
                        }
                    return MockResponse()

        runtime = AgentRuntime(llm_client=ToolCallingLLM())
        result, trace = runtime.run("查询数据")

        assert result == "查询结果是1"
        assert trace.total_steps == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
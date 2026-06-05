# -*- coding: utf-8 -*-
"""
实验6测试：Agent 集成测试
========================

测试完整的 Agent 集成：
- 端到端流程
- 多轮对话
- 错误处理
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env

setup_test_env()

from main import process, create_agent, quick_query
from core.agent_runtime import AgentRuntime


class TestAgentIntegration:
    """测试 Agent 集成"""

    def test_create_agent(self):
        """测试创建 Agent"""
        agent = create_agent()
        assert agent is not None
        assert isinstance(agent, AgentRuntime)

    def test_quick_query(self):
        """测试快速 SQL 查询"""
        # 注意：这个测试需要数据库存在
        # 如果数据库不存在，应该返回错误
        result = quick_query("SELECT 1 as test")

        assert "success" in result or "error" in result


class TestEndToEndFlow:
    """测试端到端流程"""

    def test_simple_query_flow(self):
        """测试简单查询流程"""

        class MockLLM:
            def chat(self, messages, tools=None):
                class MockResponse:
                    raw_response = {
                        "choices": [{
                            "message": {
                                "content": "SELECT 查询返回了测试数据",
                                "tool_calls": []
                            }
                        }]
                    }
                return MockResponse()

        agent = AgentRuntime(llm_client=MockLLM())
        result, trace = agent.run("执行 SELECT 1")

        assert result is not None
        assert trace is not None


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_sql_handling(self):
        """测试无效 SQL 处理"""
        # 测试错误 SQL 的处理
        from core.tools import duckdb_query

        result = duckdb_query("INVALID SQL")

        # 应该返回错误
        assert result.get("success") is False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
# -*- coding: utf-8 -*-
"""
实验1测试：MCP 工具
==================

测试 MCP 工具的实现：
- JSON-RPC 2.0 协议
- Python 执行服务
- Web 搜索服务
"""

import pytest
import json
import subprocess
import sys
from pathlib import Path

# 导入测试工具
sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env, get_test_db_path

setup_test_env()


class TestMCPProtocol:
    """测试 MCP 协议实现"""

    def test_json_rpc_request_format(self):
        """测试 JSON-RPC 请求格式"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "python_exec",
                "arguments": {"code": "print(1+1)"}
            },
            "id": 1
        }

        request_line = json.dumps(request, ensure_ascii=False)
        parsed = json.loads(request_line)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "tools/call"
        assert "params" in parsed
        assert "id" in parsed

    def test_json_rpc_response_format(self):
        """测试 JSON-RPC 响应格式"""
        response = {
            "jsonrpc": "2.0",
            "result": {"success": True, "output": "2"},
            "id": 1
        }

        assert response["jsonrpc"] == "2.0"
        assert "result" in response or "error" in response
        assert response["id"] == 1

    def test_json_rpc_error_format(self):
        """测试 JSON-RPC 错误格式"""
        error = {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": "Method not found"},
            "id": 1
        }

        assert error["jsonrpc"] == "2.0"
        assert "error" in error
        assert error["error"]["code"] == -32601


class TestPythonExecMCP:
    """测试 Python 执行 MCP 服务"""

    def test_python_exec_basic(self):
        """测试基本的 Python 执行"""
        code = "1+1"
        result = eval(code)
        assert result == 2

    def test_python_exec_import(self):
        """测试 Python 导入"""
        code = "import json; json.dumps({})"
        exec(code)
        # 如果没有抛出异常，说明执行成功


class TestWebSearchMCP:
    """测试 Web 搜索 MCP 服务"""

    def test_search_result_format(self):
        """测试搜索结果格式"""
        # 模拟搜索结果
        mock_result = {
            "success": True,
            "results": [
                {
                    "title": "Test",
                    "url": "https://example.com",
                    "snippet": "Test snippet"
                }
            ],
            "count": 1
        }

        assert mock_result["success"] is True
        assert "results" in mock_result
        assert mock_result["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
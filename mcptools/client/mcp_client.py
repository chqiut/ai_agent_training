# -*- coding: utf-8 -*-
"""
MCP Client 封装：mcp_client.py
============================

本模块实现 MCP（Model Context Protocol）客户端。

MCP 是一个标准化协议，用于：
1. LLM 与外部工具/服务之间的通信
2. 基于 JSON-RPC 2.0 规范
3. 支持stdio传输（标准输入输出）

为什么使用 MCP：
- 标准化接口：不同工具可以用相同协议通信
- 沙盒执行：工具在独立进程中运行，更安全
- 易于扩展：新工具只需实现 MCP 协议即可

实验1内容：
    实现支持 MCP 协议的工具调用。
"""

import json
import subprocess
from typing import Any, Optional


class MCPClient:
    """
    MCP 客户端

    通过标准输入输出与 MCP 服务进程通信。

    MCP 协议基于 JSON-RPC 2.0：
    - 请求：{"jsonrpc": "2.0", "method": "tool_name", "params": {...}, "id": 1}
    - 响应：{"jsonrpc": "2.0", "result": {...}, "id": 1}
    - 错误：{"jsonrpc": "2.0", "error": {...}, "id": 1}
    """

    def __init__(self, command: list[str]):
        """
        初始化 MCP 客户端

        Args:
            command: 启动 MCP服务的命令
                    例如：["python", "python_exec_mcp.py"]
        """
        self.command = command
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0

    def connect(self) -> None:
        """连接到 MCP 服务（启动子进程）"""
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

    def disconnect(self) -> None:
        """断开连接（终止子进程）"""
        if self.process:
            self.process.terminate()
            self.process.wait()

    def _send_request(self, method: str, params: dict) -> dict:
        """
        发送 JSON-RPC 请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            响应结果
        """
        if not self.process:
            raise RuntimeError("未连接到 MCP 服务")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self.request_id
        }

        # 发送请求
        request_line = json.dumps(request, ensure_ascii=False)
        self.process.stdin.write(request_line + "\n")
        self.process.stdin.flush()

        # 读取响应
        response_line = self.process.stdout.readline()
        response = json.loads(response_line)

        # 检查错误
        if "error" in response:
            raise RuntimeError(f"MCP 错误: {response['error']}")

        return response.get("result", {})

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        return self._send_request(tool_name, arguments)

    def list_tools(self) -> list[dict]:
        """
        列出所有可用工具

        Returns:
            工具列表
        """
        return self._send_request("tools/list", {})

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python 执行 MCP 服务：python_exec_mcp.py
=====================================

本模块实现了一个 MCP工具服务，用于安全地执行 Python 代码。

MCP 服务通过标准输入输出（stdio）通信：
- 接收 JSON-RPC 2.0 请求
- 执行 Python 代码
- 返回 JSON-RPC 2.0 响应

这使得 AI Agent 可以安全地执行 Python 代码进行计算。

使用方式：
    python python_exec_mcp.py
    # 然后通过 stdin/stdout 发送 JSON-RPC 请求
"""

import json
import sys
import io
import contextlib


def execute_python(code: str) -> dict:
    """
    执行 Python 代码

    Args:
        code: 要执行的 Python 代码

    Returns:
        包含执行结果的字典
    """
    output = io.StringIO()
    error_output = io.StringIO()

    try:
        with contextlib.redirect_stdout(output):
            with contextlib.redirect_stderr(error_output):
                exec(code, {"__name__": "__main__"})

        return {
            "success": True,
            "output": output.getvalue(),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "output": output.getvalue(),
            "error": f"{type(e).__name__}: {str(e)}"
        }


def handle_request(request: dict) -> dict:
    """
    处理 JSON-RPC 请求

    Args:
        request: JSON-RPC 请求对象

    Returns:
        JSON-RPC 响应对象
    """
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "tools/call":
        # 工具调用请求
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "python_exec":
            result = execute_python(arguments.get("code", ""))
        else:
            result = {"success": False, "error": f"未知工具: {tool_name}"}

        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": req_id
        }

    elif method == "tools/list":
        # 工具列表请求
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "python_exec",
                        "description": "执行 Python 代码",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"}
                            },
                            "required": ["code"]
                        }
                    }
                ]
            },
            "id": req_id
        }

    else:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"未知方法: {method}"},
            "id": req_id
        }


def main():
    """主循环：读取请求、处理、响应"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False), flush=True)
        except json.JSONDecodeError:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "无效的 JSON"},
                "id": None
            }
            print(json.dumps(error_response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web 搜索 MCP 服务：web_search_mcp.py
=================================

本模块实现了一个 MCP 工具服务，用于搜索互联网。

使用 DuckDuckGo 搜索，无需 API Key。

使用方式：
    python web_search_mcp.py
    # 然后通过 stdin/stdout 发送 JSON-RPC 请求
"""

import json
import sys


def web_search(query: str) -> dict:
    """
    执行网络搜索

    Args:
        query: 搜索关键词

    Returns:
        搜索结果
    """
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        formatted_results = []
        for r in results:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })

        return {
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results)
        }

    except ImportError:
        return {
            "success": False,
            "error": "需要安装 duckduckgo-search: pip install duckduckgo-search",
            "results": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
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
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "web_search":
            result = web_search(arguments.get("query", ""))
        else:
            result = {"success": False, "error": f"未知工具: {tool_name}"}

        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": req_id
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "web_search",
                        "description": "搜索互联网获取信息",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            },
                            "required": ["query"]
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
    """主循环"""
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
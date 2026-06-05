# -*- coding: utf-8 -*-
"""
设置 Hugging Face 镜像（国内加速）
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

"""
工具注册与分发：tools.py
========================

本模块负责：
1. 工具注册（将工具加入注册表）
2. 工具分发（根据名称调用对应工具）
3. 工具执行（运行工具并返回结果）

Tool Dispatcher（工具分发器）是 ReAct 循环的关键组件：
- 它接收 LLM 生成的工具调用请求
- 根据工具名称找到对应的工具函数
- 传入参数并执行
- 返回执行结果给 LLM

设计模式：
    使用注册表模式（Registry Pattern）：
    - 所有工具注册到一个字典中
    - 通过工具名称查找和调用
    - 方便扩展新的工具

实验2内容：
    实现 DuckDB 查询、搜索、Python 执行等工具。
"""

import json
import re
from typing import Any, Callable, Optional
from pathlib import Path

# =============================================================================
# 工具注册表
# =============================================================================

# 工具注册表：工具名称 -> 工具函数
# 这是一个全局注册表，所有工具都在这里注册
TOOL_REGISTRY: dict[str, Callable] = {}


def register_tool(name: str):
    """
    工具注册装饰器

    使用方式：
        @register_tool("my_tool")
        def my_tool_function(arg1, arg2):
            ...

    Args:
        name: 工具名称，必须与 tool_schemas.py 中的名称一致
    """
    def decorator(func: Callable) -> Callable:
        TOOL_REGISTRY[name] = func
        return func
    return decorator


# =============================================================================
# 工具实现
# =============================================================================

def _init_duckdb():
    """初始化 DuckDB 连接（延迟导入）"""
    import duckdb
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    db_path = project_root / "duckdb" / "agent.db"

    if not db_path.exists():
        raise FileNotFoundError(
            f"DuckDB 数据库不存在，请先运行 generate_data.py\n"
            f"期望路径: {db_path}"
        )

    conn = duckdb.connect(str(db_path))
    # 注册日期转换器，处理 DuckDB 返回的 date 类型
    conn.execute("CREATE OR REPLACE FUNCTION strftime(format, date) AS FORMAT")
    return conn


@register_tool("duckdb_query")
def duckdb_query(sql: str) -> dict[str, Any]:
    """
    执行 DuckDB SQL 查询

    Args:
        sql: SQL 查询语句

    Returns:
        包含查询结果的字典：
        - success: 是否成功
        - columns: 列名列表
        - rows: 行数据列表
        - row_count: 结果行数
        - error: 错误信息（如果失败）
    """
    from datetime import date, datetime

    def convert_value(v):
        """将 DuckDB 返回的特殊类型转换为 JSON 兼容的类型"""
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    try:
        conn = _init_duckdb()
        result = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description] if conn.description else []

        # 转换为列表形式（JSON 兼容），处理日期类型
        rows = []
        for row in result:
            row_dict = dict(zip(columns, row))
            rows.append({k: convert_value(v) for k, v in row_dict.items()})

        conn.close()

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "columns": [],
            "rows": [],
            "row_count": 0
        }


@register_tool("web_search")
def web_search(query: str) -> dict[str, Any]:
    """
    使用 DuckDuckGo 搜索

    Args:
        query: 搜索关键词

    Returns:
        包含搜索结果的字典：
        - success: 是否成功
        - results: 结果列表，每项包含 title, url, snippet
        - error: 错误信息
    """
    try:
        # 使用 DuckDuckGo 搜索（免费，无需 API Key）
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


@register_tool("python_exec")
def python_exec(code: str) -> dict[str, Any]:
    """
    执行 Python 代码

    Args:
        code: 要执行的 Python 代码

    Returns:
        包含执行结果的字典：
        - success: 是否成功
        - output: stdout 输出
        - error: 错误信息（如果失败）
    """
    import io
    import sys
    import contextlib

    output = io.StringIO()
    error_output = io.StringIO()

    try:
        # 捕获 stdout
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


def _init_faiss_index():
    """初始化 FAISS 索引（延迟导入）"""
    import faiss
    import pickle
    from pathlib import Path

    project_root = Path(__file__).parent.parent
    index_path = project_root / "faiss_index" / "index.faiss"
    docs_path = project_root / "faiss_index" / "index.pkl"

    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS 索引不存在，请先运行 build_index.py\n"
            f"期望路径: {index_path}"
        )

    index = faiss.read_index(str(index_path))

    with open(docs_path, 'rb') as f:
        documents = pickle.load(f)

    return index, documents


@register_tool("rag_retrieve")
def rag_retrieve(query: str, top_k: int = 3) -> dict[str, Any]:
    """
    从 FAISS 向量数据库检索

    Args:
        query: 检索查询
        top_k: 返回最相似的结果数量

    Returns:
        包含检索结果的字典：
        - success: 是否成功
        - results: 文档列表，每项包含 content, metadata, score
        - error: 错误信息
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        index, documents = _init_faiss_index()

        # 加载向量化模型并编码查询
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        query_vector = model.encode([query])
        faiss.normalize_L2(query_vector)

        # 搜索最相似的文档
        distances, indices = index.search(query_vector, top_k)

        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(documents):
                doc = documents[idx]
                results.append({
                    "rank": i + 1,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": float(dist)
                })

        return {
            "success": True,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


@register_tool("skill_load")
def skill_load(skill_name: str) -> dict[str, Any]:
    """
    加载 Skill 剧本

    Args:
        skill_name: Skill 名称（不含 .md）

    Returns:
        包含加载结果的字典：
        - success: 是否成功
        - content: 剧本内容（如果成功）
        - error: 错误信息
    """
    try:
        from pathlib import Path

        project_root = Path(__file__).parent.parent
        skill_path = project_root / "skills" / f"{skill_name}.md"

        if not skill_path.exists():
            return {
                "success": False,
                "error": f"Skill '{skill_name}' 不存在，路径: {skill_path}",
                "content": None
            }

        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            "success": True,
            "content": content,
            "skill_name": skill_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": None
        }


# =============================================================================
# 工具分发器
# =============================================================================

class ToolDispatcher:
    """
    工具分发器

    负责：
    1. 解析 LLM 的工具调用请求
    2. 调用对应的工具函数
    3. 格式化返回结果

    使用方式：
        dispatcher = ToolDispatcher()
        result = dispatcher.dispatch("duckdb_query", {"sql": "SELECT * FROM sales_fact LIMIT 5"})
    """

    def __init__(self):
        """初始化分发器"""
        self.registry = TOOL_REGISTRY

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        分发工具调用

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        if tool_name not in self.registry:
            return {
                "success": False,
                "error": f"未知工具: {tool_name}",
                "available_tools": list(self.registry.keys())
            }

        tool_func = self.registry[tool_name]

        try:
            result = tool_func(**arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"工具执行失败: {e}",
                "tool": tool_name
            }

    def dispatch_from_llm_response(self, assistant_message: dict) -> list[dict]:
        """
        从 LLM 响应中解析并执行工具调用

        当 LLM 返回 tool_calls 时，调用此方法执行所有工具调用。

        Args:
            assistant_message: LLM 返回的 assistant 消息，包含 tool_calls

        Returns:
            工具执行结果列表
        """
        results = []

        tool_calls = assistant_message.get("tool_calls", [])
        if not tool_calls:
            return results

        for call in tool_calls:
            tool_name = call["function"]["name"]
            arguments = call["function"]["arguments"]

            # 解析 JSON 参数（arguments可能是字符串）
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    results.append({
                        "success": False,
                        "error": f"参数解析失败: {arguments}",
                        "tool": tool_name
                    })
                    continue

            # 执行工具调用
            result = self.dispatch(tool_name, arguments)
            result["tool"] = tool_name
            result["call_id"] = call.get("id", "")

            results.append(result)

        return results

    def list_available_tools(self) -> list[str]:
        """列出所有可用工具"""
        return list(self.registry.keys())


# =============================================================================
# 全局分发器实例
# =============================================================================

# 全局工具分发器，供其他模块使用
dispatcher = ToolDispatcher()
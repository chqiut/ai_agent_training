# -*- coding: utf-8 -*-
"""
实验2测试：Function Calling
=========================

测试 Function Calling 的实现：
- Tool Schema 定义
- LLM 工具调用决策
- 工具参数生成
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests._common import setup_test_env

setup_test_env()

from core.tool_schemas import (
    ALL_TOOL_SCHEMAS,
    DUCKDB_QUERY_SCHEMA,
    WEB_SEARCH_SCHEMA,
    PYTHON_EXEC_SCHEMA,
    RAG_RETRIEVE_SCHEMA,
    get_tool_schema,
    get_all_tool_names
)


class TestToolSchemas:
    """测试工具 Schema 定义"""

    def test_all_schemas_exist(self):
        """测试所有 Schema 都已定义"""
        assert len(ALL_TOOL_SCHEMAS) > 0
        assert len(ALL_TOOL_SCHEMAS) == 5

    def test_duckdb_schema(self):
        """测试 DuckDB Schema"""
        schema = DUCKDB_QUERY_SCHEMA
        func = schema["function"]

        assert func["name"] == "duckdb_query"
        assert "description" in func
        assert "parameters" in func

        params = func["parameters"]
        assert params["type"] == "object"
        assert "sql" in params["properties"]
        assert "required" in params
        assert "sql" in params["required"]

    def test_web_search_schema(self):
        """测试 Web 搜索 Schema"""
        schema = WEB_SEARCH_SCHEMA
        func = schema["function"]

        assert func["name"] == "web_search"
        params = func["parameters"]
        assert "query" in params["properties"]

    def test_python_exec_schema(self):
        """测试 Python 执行 Schema"""
        schema = PYTHON_EXEC_SCHEMA
        func = schema["function"]

        assert func["name"] == "python_exec"
        params = func["parameters"]
        assert "code" in params["properties"]

    def test_rag_retrieve_schema(self):
        """测试 RAG 检索 Schema"""
        schema = RAG_RETRIEVE_SCHEMA
        func = schema["function"]

        assert func["name"] == "rag_retrieve"
        params = func["parameters"]
        assert "query" in params["properties"]
        assert "top_k" in params["properties"]

    def test_get_tool_schema(self):
        """测试通过名称获取 Schema"""
        schema = get_tool_schema("duckdb_query")
        assert schema is not None
        assert schema["function"]["name"] == "duckdb_query"

    def test_get_tool_schema_not_found(self):
        """测试获取不存在的 Schema"""
        schema = get_tool_schema("nonexistent_tool")
        assert schema is None

    def test_get_all_tool_names(self):
        """测试获取所有工具名称"""
        names = get_all_tool_names()

        assert "duckdb_query" in names
        assert "web_search" in names
        assert "python_exec" in names
        assert "rag_retrieve" in names
        assert "skill_load" in names


class TestToolSchemasCompatibility:
    """测试 Schema 与注册表的兼容性"""

    def test_schema_names_match_registry(self):
        """测试 Schema名称与 TOOL_REGISTRY 键一致"""
        from core.tools import TOOL_REGISTRY

        schema_names = get_all_tool_names()
        registry_names = list(TOOL_REGISTRY.keys())

        for name in schema_names:
            assert name in registry_names, f"Schema {name} not in registry"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
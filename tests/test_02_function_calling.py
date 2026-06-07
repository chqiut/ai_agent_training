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
    FILE_READ_SCHEMA,
    FILE_WRITE_SCHEMA,
    HTTP_REQUEST_SCHEMA,
    MARKDOWN_RENDER_SCHEMA,
    get_tool_schema,
    get_all_tool_names
)


class TestToolSchemas:
    """测试工具 Schema 定义"""

    def test_all_schemas_exist(self):
        """测试所有 Schema 都已定义"""
        assert len(ALL_TOOL_SCHEMAS) > 0
        assert len(ALL_TOOL_SCHEMAS) == 10  # 6 original + 4 new

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
        assert "file_read" in names
        assert "file_write" in names
        assert "http_request" in names
        assert "markdown_render" in names

    def test_file_read_schema(self):
        """测试文件读取 Schema"""
        schema = FILE_READ_SCHEMA
        func = schema["function"]

        assert func["name"] == "file_read"
        params = func["parameters"]
        assert "file_path" in params["properties"]
        assert "encoding" in params["properties"]

    def test_file_write_schema(self):
        """测试文件写入 Schema"""
        schema = FILE_WRITE_SCHEMA
        func = schema["function"]

        assert func["name"] == "file_write"
        params = func["parameters"]
        assert "file_path" in params["properties"]
        assert "content" in params["properties"]
        assert "content" in params["required"]

    def test_http_request_schema(self):
        """测试 HTTP 请求 Schema"""
        schema = HTTP_REQUEST_SCHEMA
        func = schema["function"]

        assert func["name"] == "http_request"
        params = func["parameters"]
        assert "url" in params["properties"]
        assert "method" in params["properties"]
        assert params["properties"]["method"]["enum"] == ["GET", "POST"]

    def test_markdown_render_schema(self):
        """测试 Markdown 渲染 Schema"""
        schema = MARKDOWN_RENDER_SCHEMA
        func = schema["function"]

        assert func["name"] == "markdown_render"
        params = func["parameters"]
        assert "content" in params["properties"]
        assert "style" in params["properties"]


class TestToolSchemasCompatibility:
    """测试 Schema 与注册表的兼容性"""

    def test_schema_names_match_registry(self):
        """测试 Schema名称与 TOOL_REGISTRY 键一致"""
        from core.tools import TOOL_REGISTRY

        schema_names = get_all_tool_names()
        registry_names = list(TOOL_REGISTRY.keys())

        for name in schema_names:
            assert name in registry_names, f"Schema {name} not in registry"


class TestFileReadTool:
    """测试 file_read 工具"""

    def test_file_read_readme(self):
        """测试读取 README.md"""
        from core.tools import file_read

        result = file_read("README.md")
        assert result["success"] is True
        assert result["content"] is not None
        assert len(result["content"]) > 0

    def test_file_read_nonexistent(self):
        """测试读取不存在的文件"""
        from core.tools import file_read

        result = file_read("nonexistent_file_12345.md")
        assert result["success"] is False
        assert "error" in result

    def test_file_read_outside_project(self):
        """测试读取项目外部文件（安全检查）"""
        from core.tools import file_read

        # 尝试读取项目外部的文件
        result = file_read("../etc/passwd")
        assert result["success"] is False


class TestFileWriteTool:
    """测试 file_write 工具"""

    def test_file_write_create(self):
        """测试创建新文件"""
        from core.tools import file_write

        result = file_write("test_output.txt", "Hello, World!")
        assert result["success"] is True
        assert result["file_path"] == "test_output.txt"

        # 验证文件确实被创建
        from core.tools import file_read
        read_result = file_read("test_output.txt")
        assert read_result["success"] is True
        assert read_result["content"] == "Hello, World!"

    def test_file_write_forbidden_extension(self):
        """测试禁止写入可执行文件"""
        from core.tools import file_write

        result = file_write("test_script.py", "print('hello')")
        assert result["success"] is False
        assert "禁止写入" in result["error"]

    def test_file_write_outside_project(self):
        """测试写入项目外部（安全检查）"""
        from core.tools import file_write

        result = file_write("../etc/test.txt", "test")
        assert result["success"] is False


class TestHttpRequestTool:
    """测试 http_request 工具"""

    def test_http_request_get(self):
        """测试 HTTP GET 请求"""
        from core.tools import http_request

        result = http_request("https://httpbin.org/get", method="GET")
        assert result["success"] is True
        assert result["status_code"] == 200
        assert "body" in result

    def test_http_request_invalid_url(self):
        """测试无效 URL"""
        from core.tools import http_request

        result = http_request("ftp://invalid-url.com")
        assert result["success"] is False


class TestMarkdownRenderTool:
    """测试 markdown_render 工具"""

    def test_markdown_render_basic(self):
        """测试基本 Markdown 渲染"""
        from core.tools import markdown_render

        result = markdown_render("# Hello\n\nThis is a test.")
        assert result["success"] is True
        assert "<h1>" in result["html"]
        assert "Hello" in result["html"]

    def test_markdown_render_with_style(self):
        """测试带样式的渲染"""
        from core.tools import markdown_render

        result = markdown_render("## Title", style="dark")
        assert result["success"] is True
        assert result["style"] == "dark"

    def test_markdown_render_code(self):
        """测试代码块渲染"""
        from core.tools import markdown_render

        md_content = "```python\nprint('hello')\n```"
        result = markdown_render(md_content)
        assert result["success"] is True
        assert "<pre>" in result["html"]
        assert "<code " in result["html"]  # Note: check for "<code " not "<code>" since attributes follow


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
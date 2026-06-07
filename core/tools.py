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
        # 使用 ddgs（DuckDuckGo 搜索的新包名）
        from ddgs import DDGS

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
            "error": "需要安装 ddgs: pip install ddgs",
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


def _parse_skill_frontmatter(content: str) -> dict:
    """
    解析 Skill 文件的 YAML frontmatter

    Args:
        content: 文件完整内容

    Returns:
        包含 metadata 和 body 的字典
    """
    import re

    # 检查是否有 frontmatter
    pattern = r'^---\n(.*?)\n---\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if match:
        frontmatter_text = match.group(1)
        body = match.group(2)

        # 简单解析 YAML frontmatter（支持基础字段）
        metadata = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':',1)
                key = key.strip()
                value = value.strip()

                # 解析列表格式 [item1, item2]
                if value.startswith('[') and value.endswith(']'):
                    items = [item.strip() for item in value[1:-1].split(',')]
                    metadata[key] = items
                else:
                    metadata[key] = value

        return {"metadata": metadata, "body": body}

    # 没有 frontmatter，返回默认结构
    return {"metadata": {}, "body": content}


@register_tool("skill_load")
def skill_load(skill_name: str) -> dict[str, Any]:
    """
    加载 Skill 剧本（支持 YAML frontmatter 元数据）

    Args:
        skill_name: Skill 名称（不含 .md）

    Returns:
        包含加载结果的字典：
        - success: 是否成功
        - content: 剧本正文内容
        - metadata: frontmatter 元数据（如果存在）
        - skill_name: skill 名称
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
                "content": None,
                "metadata": None
            }

        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 frontmatter
        parsed = _parse_skill_frontmatter(content)

        return {
            "success": True,
            "content": parsed["body"],
            "metadata": parsed["metadata"],
            "skill_name": skill_name
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": None,
            "metadata": None
        }


# =============================================================================
# 文件操作工具
# =============================================================================

# 禁止写入的可执行文件扩展名
FORBIDDEN_EXTENSIONS = {'.exe', '.py', '.sh', '.bat', '.cmd', '.ps1', '.js', '.ts'}

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


def _validate_file_path(file_path: str, allow_write: bool = False) -> tuple[bool, str]:
    """
    验证文件路径的安全性

    Args:
        file_path: 文件路径
        allow_write: 是否允许写入

    Returns:
        (是否安全, 错误信息)
    """
    try:
        # 解析为绝对路径
        abs_path = (PROJECT_ROOT / file_path).resolve()

        # 检查是否在项目目录内
        if not str(abs_path).startswith(str(PROJECT_ROOT.resolve())):
            return False, f"路径必须在项目目录内: {PROJECT_ROOT}"

        # 检查文件是否存在（读取时）
        if not allow_write and not abs_path.exists():
            return False, f"文件不存在: {file_path}"

        # 检查扩展名（写入时）
        if allow_write:
            for ext in FORBIDDEN_EXTENSIONS:
                if abs_path.name.lower().endswith(ext):
                    return False, f"禁止写入可执行文件: {abs_path.name}"

        return True, ""

    except Exception as e:
        return False, f"路径验证失败: {e}"


@register_tool("file_read")
def file_read(file_path: str, encoding: str = "utf-8") -> dict[str, Any]:
    """
    读取本地文件内容

    Args:
        file_path: 要读取的文件路径（相对于项目根目录）
        encoding: 文件编码，默认为 utf-8

    Returns:
        包含读取结果的字典：
        - success: 是否成功
        - content: 文件内容（如果成功）
        - error: 错误信息（如果失败）
    """
    try:
        # 验证路径安全性
        safe, error = _validate_file_path(file_path, allow_write=False)
        if not safe:
            return {"success": False, "error": error, "content": None}

        abs_path = (PROJECT_ROOT / file_path).resolve()

        # 检查文件大小（最大 1MB）
        if abs_path.stat().st_size > 1024 * 1024:
            return {
                "success": False,
                "error": f"文件太大，最大支持 1MB: {file_path}",
                "content": None
            }

        # 读取文件内容
        with open(abs_path, 'r', encoding=encoding) as f:
            content = f.read()

        return {
            "success": True,
            "content": content,
            "file_path": file_path,
            "size": len(content)
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": f"文件编码错误，请尝试其他编码: {encoding}",
            "content": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "content": None
        }


@register_tool("file_write")
def file_write(file_path: str, content: str, encoding: str = "utf-8") -> dict[str, Any]:
    """
    写入内容到本地文件

    Args:
        file_path: 要写入的文件路径（相对于项目根目录）
        content: 要写入的内容
        encoding: 文件编码，默认为 utf-8

    Returns:
        包含写入结果的字典：
        - success: 是否成功
        - file_path: 写入的文件路径
        - error: 错误信息（如果失败）
    """
    try:
        # 验证路径安全性
        safe, error = _validate_file_path(file_path, allow_write=True)
        if not safe:
            return {"success": False, "error": error, "file_path": None}

        abs_path = (PROJECT_ROOT / file_path).resolve()

        # 检查内容大小（最大 1MB）
        if len(content.encode('utf-8')) > 1024 * 1024:
            return {
                "success": False,
                "error": f"内容太大，最大支持 1MB",
                "file_path": None
            }

        # 确保父目录存在
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件内容
        with open(abs_path, 'w', encoding=encoding) as f:
            f.write(content)

        return {
            "success": True,
            "file_path": file_path,
            "size": len(content)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_path": None
        }


@register_tool("html_generate")
def html_generate(topic: str, style: str, pages: list[dict]) -> dict[str, Any]:
    """
    生成 HTML 演示文稿

    Args:
        topic: 演示文稿主题
        style: 样式名称（目前支持: dark_botanical）
        pages: 页面内容列表，每项包含:
            - title: 页面标题
            - content: 内容（根据 content_type 不同格式）
            - content_type: 内容类型 (text/data/trends)

    Returns:
        包含生成结果的字典：
        - success: 是否成功
        - html: 生成的 HTML 代码
        - file_path: 保存的文件路径
        - error: 错误信息（如果失败）

    使用示例：
        html_generate(
            topic="餐饮行业分析",
            style="dark_botanical",
            pages=[
                {"title": "行业现状", "content_type": "text", "content": "描述文字..."},
                {"title": "关键数据", "content_type": "data", "content": [
                    {"value": "5.6万亿", "label": "市场规模"},
                    {"value": "30%", "label": "连锁化率"}
                ]},
                {"title": "发展趋势", "content_type": "trends", "content": [
                    {"icon": "📱", "title": "数字化", "description": "..."}
                ]}
            ]
        )
    """
    try:
        from pathlib import Path
        import re

        # 延迟导入模板
        from templates.presentations.dark_botanical import (
            DARK_BOTANICAL_TEMPLATE,
            generate_slide_title,
            generate_slide_data,
            generate_slide_trends,
            generate_slide_content,
        )

        project_root = Path(__file__).parent.parent

        # 生成安全的文件名
        safe_topic = re.sub(r'[^\w\s一-鿿-]', '', topic)
        safe_topic = re.sub(r'\s+', '_', safe_topic)[:30]
        output_dir = project_root / "output"
        output_dir.mkdir(exist_ok=True)
        file_path = output_dir / f"{safe_topic}_presentation.html"

        # 构建幻灯片
        slides_html = ""

        for i, page in enumerate(pages):
            page_title = page.get("title", f"第{i+1}页")
            content_type = page.get("content_type", "text")
            content = page.get("content", "")

            if i == 0 and content_type == "text" and len(pages) > 1:
                # 第一页作为标题页
                slides_html += generate_slide_title(page_title, content if isinstance(content, str) else "")
            elif content_type == "data":
                # 数据卡片页
                slides_html += generate_slide_data(page_title, content)
            elif content_type == "trends":
                # 趋势列表页
                slides_html += generate_slide_trends(page_title, content)
            else:
                # 普通文本页
                content_str = content if isinstance(content, str) else str(content)
                slides_html += generate_slide_content(page_title, content_str)

        # 使用模板生成完整 HTML
        html = DARK_BOTANICAL_TEMPLATE.format(
            title=topic,
            slides=slides_html
        )

        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return {
            "success": True,
            "html": html,
            "file_path": str(file_path),
            "topic": topic,
            "style": style,
            "page_count": len(pages)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "html": None,
            "file_path": None
        }


# =============================================================================
# HTTP 请求工具
# =============================================================================

@register_tool("http_request")
def http_request(url: str, method: str = "GET", headers: dict = None, body: str = None, timeout: int = 30) -> dict[str, Any]:
    """
    发送 HTTP 请求调用外部 API

    Args:
        url: 请求的 URL 地址
        method: HTTP 方法（GET 或 POST），默认 GET
        headers: 请求头字典，默认 {}
        body: 请求体（POST 时使用），默认 None
        timeout: 超时秒数，默认 30

    Returns:
        包含请求结果的字典：
        - success: 是否成功
        - status_code: HTTP 状态码
        - headers: 响应头
        - body: 响应体
        - error: 错误信息（如果失败）
    """
    import urllib.request
    import urllib.parse
    import json

    if headers is None:
        headers = {}

    try:
        # 验证 URL
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme not in ('http', 'https'):
            return {
                "success": False,
                "error": "仅支持 HTTP 和 HTTPS 协议",
                "status_code": None,
                "headers": None,
                "body": None
            }

        # 限制超时
        if timeout > 60:
            timeout = 60

        # 构建请求
        req = urllib.request.Request(url, method=method.upper())

        # 添加请求头
        for key, value in headers.items():
            req.add_header(key, value)

        # 添加默认 Content-Type（如果未指定且有 body）
        if body and 'Content-Type' not in headers:
            req.add_header('Content-Type', 'application/json')

        # 添加请求体（POST）
        if body:
            if isinstance(body, dict):
                body = json.dumps(body)
            req.data = body.encode('utf-8')

        # 发送请求
        with urllib.request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode('utf-8')
            response_headers = dict(response.headers)

            return {
                "success": True,
                "status_code": response.status,
                "headers": response_headers,
                "body": response_body,
                "url": url,
                "method": method
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        return {
            "success": False,
            "error": f"HTTP {e.code}: {e.reason}",
            "status_code": e.code,
            "headers": dict(e.headers) if e.headers else None,
            "body": error_body,
            "url": url,
            "method": method
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"连接失败: {e.reason}",
            "status_code": None,
            "headers": None,
            "body": None,
            "url": url,
            "method": method
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "status_code": None,
            "headers": None,
            "body": None,
            "url": url,
            "method": method
        }


# =============================================================================
# Markdown 渲染工具
# =============================================================================

@register_tool("markdown_render")
def markdown_render(content: str, style: str = "github") -> dict[str, Any]:
    """
    将 Markdown 内容渲染为 HTML

    Args:
        content: Markdown 内容
        style: 样式主题（github/dark/code），默认 github

    Returns:
        包含渲染结果的字典：
        - success: 是否成功
        - html: 生成的 HTML 代码
        - file_path: 保存的文件路径（可选）
        - error: 错误信息（如果失败）
    """
    import re
    from pathlib import Path

    try:
        def escape_html(text):
            """转义 HTML 特殊字符"""
            return (text
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;'))

        def render_inline(text):
            """渲染行内元素"""
            # 粗体
            text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
            # 斜体
            text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
            # 行内代码
            text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
            return text

        html_parts = []
        lines = content.split('\n')
        in_code_block = False
        code_lang = ""
        code_buffer = []

        for line in lines:
            # 代码块处理
            if line.strip().startswith('```'):
                if not in_code_block:
                    # 提取语言标识
                    lang_match = re.match(r'```(\w*)', line.strip())
                    code_lang = lang_match.group(1) if lang_match else ""
                    in_code_block = True
                    code_buffer = []
                else:
                    # 代码块结束
                    code = '\n'.join(code_buffer)
                    escaped_code = escape_html(code)
                    lang_class = f' language="{code_lang}"' if code_lang else ''
                    html_parts.append(f'<pre><code{lang_class}>{escaped_code}</code></pre>')
                    in_code_block = False
                    code_lang = ""
                    code_buffer = []
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # 标题
            if line.startswith('### '):
                html_parts.append(f'<h3>{render_inline(line[4:])}</h3>')
            elif line.startswith('## '):
                html_parts.append(f'<h2>{render_inline(line[3:])}</h2>')
            elif line.startswith('# '):
                html_parts.append(f'<h1>{render_inline(line[2:])}</h1>')
            # 列表
            elif line.startswith('- '):
                html_parts.append(f'<li>{render_inline(line[2:])}</li>')
            # 分割线
            elif line.strip() == '---':
                html_parts.append('<hr>')
            # 空行
            elif line.strip() == '':
                html_parts.append('<br>')
            # 普通段落
            else:
                html_parts.append(f'<p>{render_inline(line)}</p>')

        # 合并连续的 <li> 标签为 <ul>
        html = '\n'.join(html_parts)
        html = re.sub(r'(<li>.*?</li>\n?)+', lambda m: f'<ul>{m.group(0)}</ul>', html, flags=re.DOTALL)

        # 根据样式添加不同的 CSS 类和容器
        container_class = f"markdown-render markdown-{style}"

        return {
            "success": True,
            "html": html,
            "style": style,
            "content_length": len(content)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "html": None,
            "style": style
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
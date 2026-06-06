# -*- coding: utf-8 -*-
"""
工具 Schema 定义：tool_schemas.py
================================

本模块定义了 OpenAI 兼容的 Tool Schema（工具模式）。

Tool Schema 是 Function Calling 的核心，它告诉 LLM：
1. 有哪些工具可用
2. 每个工具叫什么名字
3. 每个工具需要什么参数
4. 每个工具的用途描述

为什么要用 Schema：
    LLM 本身不知道有哪些工具可用。
    我们通过 Tool Schema "告诉" LLM 可用的工具。
    LLM 会根据用户的问题，决定调用哪个工具，并生成参数。

实验2内容：
    定义 DuckDB 查询、搜索、Python 执行等工具的 schema。
"""

from typing import Any


# =============================================================================
# 工具 Schema 定义
# =============================================================================

# DuckDB SQL 查询工具
DUCKDB_QUERY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "duckdb_query",
        "description": "执行 DuckDB SQL 查询，从数据库中获取数据。\n\n"
                     "适用场景：\n"
                     "- 查询销售数据、客户信息、产品目录\n"
                     "- 进行数据分析、统计、聚合\n"
                     "- 生成报表数据\n\n"
                     "使用示例：\n"
                     "- '查看本月销售额' -> SELECT SUM(...) FROM sales_fact\n"
                     "- '找出销量最高的产品' -> SELECT * FROM top_products\n\n"
                     "返回结果为 JSON 格式，可以直接使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "要执行的 SQL 查询语句。\n\n"
                                 "注意事项：\n"
                                 "- 只支持 SELECT 查询，不支持 UPDATE/DELETE 等修改操作\n"
                                 "- 表名：sales_fact（销售事实）, product_dim（产品维度）, "
                                 "customer_dim（客户维度）, metadata_dim（元数据）\n"
                                 "- 视图：sales_summary（销售汇总）, top_products（热销产品）, "
                                 "customer_stats（客户统计）"
                }
            },
            "required": ["sql"]
        }
    }
}

# Web 搜索工具
WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "搜索互联网获取最新信息。\n\n"
                     "适用场景：\n"
                     "- 查询实时新闻、行业动态\n"
                     "- 查找不确定的事实\n"
                     "- 获取最新数据\n\n"
                     "使用示例：\n"
                     "- '搜索最新的 AI 发展趋势'\n"
                     "- '查询今天天气'\n\n"
                     "注意：这个工具使用 DuckDuckGo 搜索，不需要 API Key。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询关键词。\n\n"
                                 "建议：\n"
                                 "- 使用简洁的关键词\n"
                                 "- 中文查询自动使用中文结果\n"
                                 "- 可以包含地点、时间等限定词"
                }
            },
            "required": ["query"]
        }
    }
}

# Python 代码执行工具
PYTHON_EXEC_SCHEMA = {
    "type": "function",
    "function": {
        "name": "python_exec",
        "description": "执行 Python 代码进行计算和数据处理。\n\n"
                     "适用场景：\n"
                     "-复杂数学计算\n"
                     "- 数据处理和转换\n"
                     "- 调用外部库（pandas, numpy 等）\n"
                     "- 执行本地文件操作\n\n"
                     "使用示例：\n"
                     "- '计算 1-100 的所有素数'\n"
                     "- '读取 CSV 文件并计算平均值'\n"
                     "- '绘制一个折线图'\n\n"
                     "注意：\n"
                     "- 代码在沙盒环境中执行\n"
                     "- 可以 import常用库（pandas, numpy, matplotlib）\n"
                     "- 执行时间限制 30 秒\n"
                     "- 只返回 stdout 输出和错误信息",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码。\n\n"
                                 "格式要求：\n"
                                 "-必须是完整的、可执行的 Python 代码\n"
                                 "- 不需要 main() 函数包装\n"
                                 "- print() 输出会被捕获并返回\n"
                                 "- 建议添加适当的注释说明代码功能"
                }
            },
            "required": ["code"]
        }
    }
}

# RAG 检索工具
RAG_RETRIEVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "rag_retrieve",
        "description": "从向量数据库中检索相关的事实和知识。\n\n"
                     "适用场景：\n"
                     "- 查询历史事实和数据\n"
                     "- 检索项目相关知识\n"
                     "- 查找过去的决策和理由\n\n"
                     "使用示例：\n"
                     "- '检索之前关于某客户的讨论'\n"
                     "- '查找项目中的技术选型决策'\n"
                     "- '查询某产品的历史销售数据'\n\n"
                     "注意：\n"
                     "- 基于语义相似度检索\n"
                     "- 返回最相关的 N 条结果\n"
                     "- 可以设置相似度阈值过滤结果",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索查询。\n\n"
                                 "建议：\n"
                                 "- 使用自然语言描述要查找的内容\n"
                                 "- 可以包含上下文信息以提高检索精度\n"
                                 "- 例如：'客户 C1001 的购买记录'"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回最相关的结果数量，默认为 3。",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    }
}

# Skill 加载工具
SKILL_LOAD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "skill_load",
        "description": "动态加载 Skill 剧本，自定义 Agent 的行为。\n\n"
                     "适用场景：\n"
                     "- 处理特定类型的任务（如代码审查、数据分析）\n"
                     "- 加载专用的提示词和流程\n"
                     "- 启用特定的能力组合\n\n"
                     "使用示例：\n"
                     "- '加载行业洞察 Skill'\n"
                     "- '启用代码审查模式'\n\n"
                     "注意：\n"
                     "- Skill 剧本存储在 skills/ 目录下\n"
                     "- 加载后会更新 Agent 的提示词和行为\n"
                     "- 可以随时切换或关闭",
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Skill 剧本的名称（不含 .md 后缀）。\n\n"
                                 "可用 Skill：\n"
                                 "- industry_insight：行业洞察剧本\n"
                                 "- frontend_design_guide：前端设计指南剧本"
                }
            },
            "required": ["skill_name"]
        }
    }
}

# HTML 演示文稿生成工具
HTML_GENERATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "html_generate",
        "description": "生成 HTML 演示文稿，支持多种样式主题。\n\n"
                     "适用场景：\n"
                     "- 生成专业的演示文稿\n"
                     "- 创建数据可视化报告\n"
                     "- 制作趋势分析展示\n\n"
                     "使用示例：\n"
                     "- '生成一个关于餐饮行业分析的演示文稿'\n"
                     "- '创建一个展示销售数据的3页PPT'\n\n"
                     "样式选项：\n"
                     "- dark_botanical: 优雅深色主题，适合正式场合\n\n"
                     "页面类型：\n"
                     "- text: 普通文本页\n"
                     "- data: 数据展示页（使用 data卡片）\n"
                     "- trends: 趋势列表页",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "演示文稿的主题/标题"
                },
                "style": {
                    "type": "string",
                    "description": "样式名称，目前支持: dark_botanical",
                    "default": "dark_botanical"
                },
                "pages": {
                    "type": "array",
                    "description": "页面内容列表，每页是一个对象",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "页面标题"
                            },
                            "content_type": {
                                "type": "string",
                                "description": "内容类型: text（文本）, data（数据卡片）, trends（趋势列表）"
                            },
                            "content": {
                                "description": "页面内容，根据 content_type 不同格式不同"
                            }
                        },
                        "required": ["title", "content_type", "content"]
                    }
                }
            },
            "required": ["topic", "pages"]
        }
    }
}

# =============================================================================
# 工具列表
# =============================================================================

# 所有可用工具的 Schema 列表
# 这个列表会被传递给 LLM，让它知道有哪些工具可用
ALL_TOOL_SCHEMAS = [
    DUCKDB_QUERY_SCHEMA,
    WEB_SEARCH_SCHEMA,
    PYTHON_EXEC_SCHEMA,
    RAG_RETRIEVE_SCHEMA,
    SKILL_LOAD_SCHEMA,
    HTML_GENERATE_SCHEMA,
]


def get_tool_schema(tool_name: str) -> dict | None:
    """
    根据工具名称获取其 Schema

    Args:
        tool_name: 工具名称（如 "duckdb_query"）

    Returns:
        工具的 Schema 定义，如果不存在返回 None
    """
    for schema in ALL_TOOL_SCHEMAS:
        if schema["function"]["name"] == tool_name:
            return schema
    return None


def get_all_tool_names() -> list[str]:
    """
    获取所有工具的名称列表

    Returns:
        工具名称列表
    """
    return [schema["function"]["name"] for schema in ALL_TOOL_SCHEMAS]
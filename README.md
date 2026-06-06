# AI Agent Training

基于 **ReAct 架构** 的智能 Agent 系统，深度融合 MCP 协议、三层记忆系统、RAG 及 Skill 剧本。

## 项目概述

本项目是《AI 应用开发专家特训营》的核心教学项目，覆盖 7 个核心实验：

| 实验 | 内容 | 核心文件 |
|------|------|----------|
| 实验1 | MCP 工具搭建 | `mcptools/` |
| 实验2 | Function Calling | `core/tool_schemas.py`, `core/tools.py` |
| 实验3 | ReAct 循环 | `core/agent_runtime.py` |
| 实验4 | 三层记忆系统 | `core/memory.py` |
| 实验5 | RAG 检索 | `core/rag.py` |
| 实验6 | Skill 剧本 | `skills/` |
| 实验7 | Web API & GUI | `app.py`, `templates/` |

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│                    (Web / CLI / API)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      FastAPI Web Server │
│                      (app.py, templates/)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AgentRuntime (ReAct Loop)                    │
│                    (core/agent_runtime.py)                     │
│                                                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│   │   Reason    │→ │    Act      │→ │      Observe        │   │
│   │  (LLM思考)  │  │ (工具调用)  │  │ (结果反馈)       │   │
│   └─────────────┘  └─────────────┘  └─────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
  ┌───────────┐   ┌───────────┐    ┌───────────┐
   │  Tools    │    │  Memory   │    │   RAG     │
   │ duckdb    │    │ 三层记忆  │    │  向量检索 │
   │ web_search│    │          │    │           │
   │ python    │    │          │    │           │
   └───────────┘    └───────────┘    └───────────┘
```

## 目录结构

```
ai_agent_training/
├── core/ # 核心模块
│   ├── agent_runtime.py     # ReAct 主循环（教学重点）
│   ├── llm_client.py        # LLM API 封装
│   ├── prompts.py           # System Prompt
│   ├── tool_schemas.py      # Tool Schema 定义
│   ├── tools.py # Tool Registry & Dispatcher
│   ├── memory.py # 三层记忆系统
│   └── rag.py               # RAG 检索
├── mcptools/                # MCP 工具服务
│   ├── client/mcp_client.py
│   ├── python_exec_mcp.py
│   ├── web_search_mcp.py
│   └── start_mcp.sh
├── skills/                  # Skill 剧本
│   ├── industry_insight.md     # 行业洞察剧本
│   └── frontend_design_guide.md # 前端设计指南剧本
├── static/                  # 前端静态资源
│   ├── css/style.css
│   └── js/app.js
├── templates/               # HTML 模板
│   ├── index.html              # Web 界面模板
│   └── presentations/          # 演示文稿模板
│       └── dark_botanical.py   # Dark Botanical 风格
├── data/                    # CSV 数据文件
├── duckdb/                   # DuckDB 数据库
├── faiss_index/              # FAISS 向量索引
├── tests/                    # 测试套件
├── generate_data.py          # 生成数据
├── build_index.py # 构建索引
├── main.py # 业务逻辑入口
├── app.py                    # FastAPI Web 入口
├── requirements.txt
├── env.example
└── .env                      # 环境变量（勿提交到 Git）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 3. 生成数据

```bash
python generate_data.py
```

### 4. 构建向量索引

如果 Hugging Face 网络不通，会自动使用 TF-IDF 向量化作为备选：

```bash
python build_index.py
```

### 5. 运行 Web 服务

```bash
uvicorn app:app --reload --port 8001
# 访问 http://localhost:8001/index
```

### 6. 运行测试

```bash
python -m pytest tests/ -v
```

## 常见问题

### Hugging Face 网络超时

如果下载向量化模型失败，代码会自动使用 TF-IDF 向量化作为备选方案，不需要额外配置。

### DeepSeek API 调用失败

-确认 `.env` 文件中的 `DEEPSEEK_API_KEY` 正确
- 确认 API 账户余额充足
- 检查网络连接

## 核心概念

### ReAct 循环

ReAct = Reason + Act + Observe，是一种让 LLM 能够进行多步推理和工具使用的架构。

```
Reason: 分析问题，决定是否需要工具
   ↓
Act: 调用工具（如 SQL 查询、网页搜索）
   ↓
Observe: 获取工具结果
   ↓
循环直到任务完成
```

### 三层记忆系统

1. **短期记忆**：消息滚动窗口，保存最近 N 条对话
2. **中期记忆**：LLM 生成会话摘要，压缩关键信息
3. **长期记忆**：FAISS 向量数据库，存储历史知识

### 工具系统

- `duckdb_query`: 执行 SQL 查询
- `web_search`: 搜索互联网
- `python_exec`: 执行 Python 代码
- `rag_retrieve`: 向量数据库检索
- `skill_load`: 加载 Skill 剧本（支持 YAML frontmatter 元数据）
- `html_generate`: 生成 HTML 演示文稿（支持 text/data/trends 三种页面类型）

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | API 信息 |
| `/index` | GET | Web 界面 |
| `/chat` | POST | 聊天接口 |
| `/clear` | POST | 清空会话 |
| `/health` | GET | 健康检查 |

###聊天接口示例

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "分析本月销售额"}'
```

## 教学重点

本项目是**教学导向**的，代码中包含大量中文注释，详细解释了：

- ReAct 循环的工作原理
- System Prompt 的设计思路
- Tool Call 的解析过程
- 三层记忆的实现机制
- RAG 检索的 MMR 算法

建议按照实验顺序学习：

1. 先理解 MCP 协议（实验1）
2. 理解 Function Calling（实验2）
3. 深入 ReAct 循环（实验3）——**核心**
4. 理解记忆系统（实验4）
5. 理解 RAG（实验5）
6. 了解 Skill 剧本（实验6）
7. 体验完整系统（实验7）

## 许可证

MIT License
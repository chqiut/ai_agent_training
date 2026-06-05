# ai\_agent\_training项目构建提示词

# 无标题

**角色设定**：你是一位资深 AI 工程架构师，擅长构建生产级的智能体系统。请严格按照以下规格说明书，生成一个完整的 Python 项目。

**特别要求**：这是一个**教学与学习导向**的项目。请在代码中加入**大量、清晰、有助于理解 ReAct 架构和智能体运行机制的中文注释**。同时，请补全一个类似于 **OpenClaw** 风格的 HTML 前端界面。



## 一、项目名称与目标

**项目名称**：ai\_agent\_training**核心目标**：构建一个基于 **ReAct 架构** 的智能体，深度融合 **MCP 协议**、**三层记忆系统**、**RAG** 及 **Skill 剧本**。该项目需覆盖《AI应用开发专家特训营》的全部 7 个核心实验。

**关键数据层逻辑（务必遵守）**：

1. **业务数据（结构化）**：使用 duckdb 作为 OLAP 引擎，数据来源于 data/ 目录下的 CSV 文件。

2. **知识/记忆（非结构化）**：使用 faiss 作为向量数据库，用于存储长期事实记忆和文档检索。



## 二、项目目录结构（严格执行）

请生成以下目录结构中的所有文件：

ai\_agent\_training/

├── core/

│   ├── \_\_init\_\_\.py

│   ├── agent\_runtime\.py        \# ReAct 主循环 \(实验3\)

│   ├── llm\_client\.py           \# LLM API 封装 \(实验2\)

│   ├── prompts\.py              \# 稳定的 System Prompt

│   ├── tool\_schemas\.py         \# OpenAI tools schema 定义 \(实验2\)

│   ├── tools\.py                \# Tool Registry \& Dispatcher

│   ├── memory\.py               \# 三层记忆系统 \(实验4\)

│   └── rag\.py                  \# 文档检索 \(实验5\)

│

├── mcptools/                   \# 实验1：MCP 工具搭建

│   ├── client/

│   │   └── mcp\_client\.py       \# MCP Client 封装

│   ├── python\_exec\_mcp\.py      \# Python 执行服务

│   ├── web\_search\_mcp\.py       \# BochaAI 搜索服务

│   └── start\_mcp\.sh            \# MCP 服务启动脚本

│

├── skills/                     \# 实验6：Skill 剧本

│   └── industry\_insight\.md     \# 示例剧本

│

├── static/                     \# ✅ 新增：前端静态资源

│   ├── css/

│   │   └── style\.css           \# OpenClaw 风格样式

│   └── js/

│       └── app\.js              \# 前端交互逻辑

│

├── templates/                  \# ✅ 新增：HTML 模板

│   └── index\.html              \# OpenClaw 风格主界面

│

├── data/                       \# 原始数据

│   ├── CustomerDim\.csv

│   ├── ProductDim\.csv

│   ├── SalesFact\.csv

│   └── MetadataDim\.csv

│

├── duckdb/                     \# DuckDB 数据存储

│   └── agent\.db                \# 由 generate\_data\.py 生成

│

├── faiss\_index/                \# FAISS 向量索引

│   ├── index\.faiss

│   └── index\.pkl

│

├── tests/                      \# 实验测试套件

│   ├── \_common\.py              \# 测试环境初始化

│   ├── test\_01\_mcp\_tools\.py

│   ├── test\_02\_function\_calling\.py

│   ├── test\_03\_react\_loop\.py

│   ├── test\_04\_memory\_and\_rag\.py

│   ├── test\_05\_skill\_workflow\.py

│   ├── test\_06\_agent\_integration\.py

│   └── run\_all\.sh

│

├── generate\_data\.py             \# ✅ 关键：从 CSV 构建 DuckDB

├── build\_index\.py               \# ✅ 关键：构建 FAISS 索引

├── main\.py                      \# ✅ 核心业务逻辑入口 \(被 app\.py 调用\)

├── app\.py                       \# ✅ 实验7：FastAPI Web 入口 \(GUI\)

├── requirements\.txt

├── env\.example                  \# API Key 示例

└── README\.md



## 三、核心模块实现要求

### 1\. 数据构建（必须实现）

- **generate\_data\.py**：读取 data/\*\.csv，创建 duckdb/agent\.db。

- **build\_index\.py**：构建 FAISS 向量索引。

### 2\. 实验1：MCP 工具 \(mcptools/\)

- 使用 **stdio** 传输。

- python\_exec\_mcp\.py 和 web\_search\_mcp\.py 需实现 **JSON\-RPC 2\.0** 协议。

### 3\. 实验2：Function Calling \(core/tool\_schemas\.py\)

- 定义 OpenAI 兼容的 Schema。

### 4\. 实验3：ReAct 循环 \(core/agent\_runtime\.py\) —— **重点教学区**

- 实现单步循环：Reason → Act → Observe。

- **请在代码中详细注释**：

- **ReAct 循环的宏观流程**（为什么这是一个“思考\-行动\-观察”的循环）。

- **System Prompt 的作用**（如何约束模型的行为）。

- **Tool Call 的解析过程**（LLM 是如何“决定”调用工具的）。

- **Observation 的回传机制**（工具结果如何变成 LLM 的下一次输入）。

- **Max Steps 的必要性**（防止无限循环）。

### 5\. 实验4：记忆系统 \(core/memory\.py\)

- **短期**：消息滚动窗口。

- **中期**：LLM 生成会话摘要。

- **长期**：基于 faiss\_index 的事实检索。

### 6\. 实验5 \& 6：RAG \& Skill

- rag\.py：基于现有 FAISS 索引进行 MMR 检索。

- skills/：Agent 通过工具动态加载 Markdown 剧本。

### 7\. 实验7：Web API \& GUI \(app\.py \& templates/\)

- 使用 **FastAPI**。

- 提供 POST /chat 接口，调用 main\.process\(\) 并返回结果。

- **提供一个类似于 OpenClaw 的 GUI 界面**：

- **布局**：左侧为 Trace / 思维链展示区，右侧为聊天主界面。

- **功能**：

    - 输入框支持回车发送。

    - 实时显示 Agent 的 Thought（思考过程）和 Tool Calls（工具调用）。

    - 提供一个 "Clear" 按钮，调用 POST /clear 接口重置会话。

- **风格**：深色主题，代码高亮，Markdown 渲染。



## 四、工程规范（必须遵守）

1. **Python 版本**：3\.10\+

2. **类型注解**：所有函数参数和返回值必须有类型注解。

3. **依赖管理**：requirements\.txt 必须包含所有依赖（duckdb, faiss\-cpu, fastapi, uvicorn, requests, sentence\-transformers, jinja2 等）。

4. **安全**：**绝对禁止**在代码中硬编码 API Key，必须通过环境变量（\.env 文件）读取。

5. **解耦**：tool\_schemas\.py 中的 name 必须与 tools\.py 中的 TOOL\_REGISTRY 键完全一致。

6. **教学优先**：**代码注释的质量与本项目的成败同等重要**。请像在教学生一样写注释。



## 五、交付指令

请开始生成上述项目的**完整代码**。请确保代码是**可直接运行的**，而不仅仅是占位符。首先，请从 generate\_data\.py 和 build\_index\.py 这两个基础脚本开始生成。






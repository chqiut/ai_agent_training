# -*- coding: utf-8 -*-
"""
FastAPI Web 入口：app.py
=======================

实验7内容：
    实现 FastAPI Web 服务，提供：
    - GET /: 主页
    - POST /chat: 聊天接口
    - POST /clear: 清空会话接口

使用方法：
    uvicorn app:app --reload
    访问 http://localhost:8001
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志系统
from core.utils import setup_logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import uuid

from main import process, create_agent
from core.utils import get_logger

logger = get_logger("app")

# =============================================================================
# FastAPI 应用初始化
# =============================================================================

app = FastAPI(
    title="AI Agent Training",
    description="基于 ReAct 架构的智能数据分析助手",
    version="1.0.0"
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# 会话管理
# =============================================================================

# 存储活跃的 Agent 实例
# key: conversation_id
# value: agent instance
active_agents: dict[str, any] = {}


# =============================================================================
# 请求/响应模型
# =============================================================================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    conversation_id: str
    trace: Optional[dict] = None


class ClearRequest(BaseModel):
    """清空会话请求模型"""
    conversation_id: Optional[str] = None


class ClearResponse(BaseModel):
    """清空会话响应模型"""
    success: bool
    message: str


# =============================================================================
# 路由
# =============================================================================

@app.get("/")
async def root():
    """主页"""
    return {"message": "AI Agent Training API", "docs": "/docs"}


@app.get("/index")
async def index():
    """主页 HTML"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口

    接收用户消息，调用 Agent 处理，返回结果。

    请求体：
        message: 用户消息
        conversation_id: 会话 ID（可选）

    响应：
        response: Agent 的回复
        conversation_id: 会话 ID
        trace: 执行轨迹（可选）
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())

        # 如果有 conversation_id，尝试使用已有的 Agent
        if request.conversation_id and request.conversation_id in active_agents:
            agent = active_agents[request.conversation_id]
        else:
            # 创建新的 Agent
            agent = create_agent()
        response, trace = agent.run(request.message)

        # 序列化 trace
        trace_dict = None
        if trace:
            trace_dict = {
                "steps": [
                    {
                        "step_number": s.step_number,
                        "thought": s.thought,
                        "tool_calls": s.tool_calls,
                        "tool_results": s.tool_results,
                        "final_response": s.final_response
                    }
                    for s in trace.steps
                ],
                "total_steps": trace.total_steps,
                "completed": trace.completed,
                "error": trace.error
            }

        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id or conversation_id,
            trace=trace_dict
        )

    except Exception as e:
        logger.error(f"聊天接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口（SSE）

    使用 Server-Sent Events 流式返回 Agent 的响应，
    实现打字机效果。

    请求体：
        message: 用户消息
        conversation_id: 会话 ID（可选）

   响应：
        SSE 流，包含 text事件
    """
    from fastapi.responses import StreamingResponse
    import json

    async def event_generator():
        """SSE 事件生成器"""
        try:
            conversation_id = request.conversation_id or str(uuid.uuid4())

            # 创建 Agent
            agent = create_agent()

            # 使用流式方法
            for event in agent.run_stream(request.message):
                # event 格式: {"type": "step_start"/"thought"/"tool_call"/"final", "content": "..."}
                event_type = event.get("type", "")
                content = event.get("content", "")
                step = event.get("step", 0)

                if event_type == "final":
                    # 最终回复
                    yield f"data: {json.dumps({'type': 'final', 'content': content}, ensure_ascii=False)}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
                elif event_type == "thought":
                    yield f"data: {json.dumps({'type': 'thought', 'content': content}, ensure_ascii=False)}\n\n"
                elif event_type == "tool_call":
                    yield f"data: {json.dumps({'type': 'tool', 'content': content}, ensure_ascii=False)}\n\n"
                elif event_type == "step_start":
                    yield f"data: {json.dumps({'type': 'step', 'step': step, 'content': content}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"流式聊天错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'close'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/clear", response_model=ClearResponse)
async def clear(request: ClearRequest):
    """
    清空会话接口

    清除指定会话的 Agent 实例。

    请求体：
        conversation_id: 会话 ID（可选）

    响应：
        success: 是否成功
        message: 消息
    """
    try:
        if request.conversation_id and request.conversation_id in active_agents:
            del active_agents[request.conversation_id]

        return ClearResponse(
            success=True,
            message="会话已清空"
        )

    except Exception as e:
        logger.error(f"清空会话接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
// -*- coding: utf-8 -*-
/*
 * 前端交互逻辑：app.js
 * ====================
 *
 * 功能：
 * - 处理用户输入（回车发送）
 * - 调用后端 API
 * - 实时显示 Trace（思维链和工具调用）
 * - Markdown 渲染
 */

// ============================================================================
// 配置
// ============================================================================

const API_BASE = ''; // 空字符串表示同源

// ============================================================================
// 状态管理
// ============================================================================

let conversationId = null;
let isLoading = false;

// ============================================================================
// DOM 元素
// ============================================================================

const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const chatMessages = document.getElementById('chat-messages');
const traceContent = document.getElementById('trace-content');
const clearButton = document.getElementById('clear-button');
const conversationIdDisplay = document.getElementById('conversation-id');
const copySessionIdBtn = document.getElementById('copy-session-id');

// ============================================================================
// 工具函数
// ============================================================================

/**
 * 简单的 Markdown 渲染器
 * 支持：标题、代码、列表、粗体、斜体
 */
function renderMarkdown(text) {
    if (!text) return '';

    let html = text;

    // 转义 HTML
    html = html.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;');

    // 代码块
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

    // 行内代码
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 标题
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // 粗体
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 斜体
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 列表
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

    // 换行
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');

    return `<div class="markdown-content"><p>${html}</p></div>`;
}

/**
 * 添加消息到聊天区域
 */
function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `<div class="message-content">${renderMarkdown(content)}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * 更新会话 ID 显示
 */
function updateConversationIdDisplay(convId) {
    if (convId && conversationIdDisplay) {
        conversationIdDisplay.textContent = convId;
        conversationIdDisplay.title = convId;
    }
}

/**
 * 复制会话 ID 到剪贴板
 */
async function copySessionId() {
    if (!conversationId) {
        return;
    }

    try {
        await navigator.clipboard.writeText(conversationId);
        copySessionIdBtn.classList.add('copied');

        // 显示提示
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = '已复制会话 ID';
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
            copySessionIdBtn.classList.remove('copied');
        }, 1500);
    } catch (err) {
        console.error('复制失败:', err);
    }
}

/**
 * 添加步骤到 Trace 面板
 */
function addTraceStep(step) {
    const stepDiv = document.createElement('div');
    stepDiv.className = 'trace-step';

    // 步骤头部
    const headerDiv = document.createElement('div');
    headerDiv.className = 'step-header';
    headerDiv.innerHTML = `
        <span class="step-number">${step.step_number}</span>
        <span class="step-title">${step.tool_calls && step.tool_calls.length > 0
            ? 'Tool Call: ' + step.tool_calls.map(c => c.function.name).join(', ')
            : '思考中...'}</span>
    `;
    headerDiv.onclick = () => {
        const content = stepDiv.querySelector('.step-content');
        content.classList.toggle('expanded');
    };

    // 步骤内容
    const contentDiv = document.createElement('div');
    contentDiv.className = 'step-content expanded';

    // Thought
    if (step.thought) {
        contentDiv.innerHTML += `
            <div class="thought-section">
                <div class="thought-label">Thought</div>
                <div class="thought-content">${escapeHtml(step.thought)}</div>
            </div>
        `;
    }

    // Tool Calls
    if (step.tool_calls && step.tool_calls.length > 0) {
        for (const call of step.tool_calls) {
            contentDiv.innerHTML += `
                <div class="tool-section">
                    <div class="tool-label">Tool Call</div>
                    <div class="tool-call">
                        <div class="tool-name">${call.function.name}</div>
                        <div class="tool-args">${escapeHtml(call.function.arguments)}</div>
                    </div>
                </div>
            `;
        }
    }

    // Tool Results
    if (step.tool_results && step.tool_results.length > 0) {
        for (const result of step.tool_results) {
            const success = result.success !== false;
            contentDiv.innerHTML += `
                <div class="tool-section">
                    <div class="result-label">${success ? 'Result' : 'Error'}</div>
                    <div class="result-content">${escapeHtml(result.output || result.error || JSON.stringify(result, null, 2))}</div>
                </div>
            `;
        }
    }

    // Final Response
    if (step.final_response) {
        contentDiv.innerHTML += `
            <div class="thought-section">
                <div class="thought-label">Final Response</div>
                <div class="thought-content">${escapeHtml(step.final_response)}</div>
            </div>
        `;
    }

    stepDiv.appendChild(headerDiv);
    stepDiv.appendChild(contentDiv);
    traceContent.appendChild(stepDiv);
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
}

/**
 * 显示加载状态
 */
function showLoading() {
    isLoading = true;
    sendButton.disabled = true;
    sendButton.textContent = '思考中...';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading-indicator';
    loadingDiv.id = 'loading-indicator';
    loadingDiv.innerHTML = `
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    isLoading = false;
    sendButton.disabled = false;
    sendButton.textContent = '发送';

    const loadingDiv = document.getElementById('loading-indicator');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * 清空界面
 */
function clearUI() {
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <h3>欢迎使用 AI Agent</h3>
            <p>基于 ReAct 架构的智能数据分析助手</p>
            <p>请在下方输入您的问题</p>
        </div>
    `;
    traceContent.innerHTML = '';
    updateConversationIdDisplay(null);
}

// ============================================================================
// API 调用
// ============================================================================

/**
 * 发送消息到后端
 */
async function sendMessage(message) {
    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;

    } catch (error) {
        console.error('API 调用失败:', error);
        throw error;
    }
}

/**
 * 发送消息到后端（流式 SSE）
 * 使用 fetch + ReadableStream 替代 EventSource（EventSource 不支持 POST）
 */
async function sendMessageStream(message) {
    try {
        const response = await fetch(`${API_BASE}/chat/stream?message=${encodeURIComponent(message)}&conversation_id=${conversationId || ''}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentStepDiv = null;
        let thoughtSection = null;
        let finalResponse = '';
        let finalConversationId = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;

                try {
                    const data = JSON.parse(line.slice(6));
                    const type = data.type;
                    const content = data.content || '';

                    switch (type) {
                        case 'step':
                            // 开始新步骤
                            currentStepDiv = document.createElement('div');
                            currentStepDiv.className = 'trace-step';
                            currentStepDiv.innerHTML = `
                                <div class="step-header">
                                    <span class="step-number">${data.step}</span>
                                    <span class="step-title">步骤 ${data.step}</span>
                                </div>
                                <div class="step-content expanded">
                                    <div class="thought-section">
                                        <div class="thought-label">执行中...</div>
                                        <div class="thought-content streaming"></div>
                                    </div>
                                </div>
                            `;
                            traceContent.appendChild(currentStepDiv);
                            thoughtSection = currentStepDiv.querySelector('.thought-content');
                            break;

                        case 'thought':
                            // 思考内容
                            if (currentStepDiv) {
                                const header = currentStepDiv.querySelector('.step-header .step-title');
                                header.textContent = '思考中...';
                                if (thoughtSection) {
                                    thoughtSection.textContent = content;
                                }
                            }
                            break;

                        case 'tool':
                            // 工具调用
                            if (currentStepDiv) {
                                const header = currentStepDiv.querySelector('.step-header .step-title');
                                header.textContent = content;
                            }
                            break;

                        case 'final':
                            // 最终回复
                            finalResponse = content;
                            if (thoughtSection) {
                                thoughtSection.textContent = content;
                            }
                            break;

                        case 'done':
                            // 完成
                            finalConversationId = data.conversation_id;
                            break;

                        case 'error':
                            // 错误
                            throw new Error(content);

                        case 'close':
                            // 关闭
                            break;
                    }
                } catch (e) {
                    if (e.message) throw e;
                }
            }
        }

        return { response: finalResponse, conversation_id: finalConversationId };

    } catch (error) {
        console.error('流式请求失败:', error);
        throw error;
    }
}

// ============================================================================
// 事件处理
// ============================================================================

/**
 * 处理发送按钮点击
 */
async function handleSend() {
    if (isLoading) return;

    const message = messageInput.value.trim();
    if (!message) return;

    // 清空输入框
    messageInput.value = '';

    // 添加用户消息
    addMessage('user', message);

    // 显示加载状态
    showLoading();

    // 清空 Trace（准备新的）
    traceContent.innerHTML = '';

    try {
        // 判断是否使用流式
        if (document.getElementById('stream-toggle') && document.getElementById('stream-toggle').checked) {
            // 流式模式
            const data = await sendMessageStream(message);

            // 保存 conversation_id
            if (data.conversation_id) {
                conversationId = data.conversation_id;
                updateConversationIdDisplay(conversationId);
            }

            // 添加助手消息
            if (data.response) {
                addMessage('assistant', data.response);
            }
        } else {
            // 非流式模式
            const data = await sendMessage(message);

            // 保存 conversation_id
            if (data.conversation_id) {
                conversationId = data.conversation_id;
                updateConversationIdDisplay(conversationId);
            }

            // 添加助手消息
            if (data.response) {
                addMessage('assistant', data.response);
            }

            // 添加 Trace
            if (data.trace && data.trace.steps) {
                for (const step of data.trace.steps) {
                    addTraceStep(step);
                }
            }
        }

    } catch (error) {
        addMessage('assistant', `抱歉，发生了错误：${error.message}`);
    } finally {
        hideLoading();
    }
}

/**
 * 处理复制会话 ID 按钮点击
 */
async function handleCopySessionId() {
    await copySessionId();
}

/**
 * 处理回车发送
 */
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSend();
    }
}

/**
 * 处理清空按钮
 */
async function handleClear() {
    try {
        await fetch(`${API_BASE}/clear`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                conversation_id: conversationId
            })
        });
    } catch (error) {
        console.error('清空失败:', error);
    }

    conversationId = null;
    clearUI();
}

// ============================================================================
// 初始化
// ============================================================================

function init() {
    // 绑定事件
    sendButton.addEventListener('click', handleSend);
    messageInput.addEventListener('keypress', handleKeyPress);
    clearButton.addEventListener('click', handleClear);
    copySessionIdBtn.addEventListener('click', handleCopySessionId);

    // 自动聚焦输入框
    messageInput.focus();

    // 显示欢迎消息
    clearUI();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
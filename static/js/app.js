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
 * 保存 conversationId 到 localStorage
 */
function saveConversationId(convId) {
    if (convId) {
        localStorage.setItem('ai_agent_conv_id', convId);
    }
}

/**
 * 从 localStorage 加载 conversationId
 */
function loadConversationId() {
    return localStorage.getItem('ai_agent_conv_id');
}

/**
 * 清除 localStorage 中的 conversationId
 */
function clearStoredConversationId() {
    localStorage.removeItem('ai_agent_conv_id');
}

/**
 * 简单的 Markdown 渲染器
 * 支持：标题、代码、列表、粗体、斜体
 */

/**
 * 加载会话历史
 */
async function loadConversationHistory(convId) {
    try {
        const response = await fetch(`${API_BASE}/chat/history?conversation_id=${convId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        return data.messages || [];
    } catch (error) {
        console.error('加载会话历史失败:', error);
        return [];
    }
}
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
    stepDiv.className = 'ReAct-step';

    // 步骤编号指示器
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'step-indicator';
    indicatorDiv.innerHTML = `
        <span class="step-badge">${step.step_number}</span>
        <span>ReAct 步骤</span>
    `;
    stepDiv.appendChild(indicatorDiv);

    // Thought 块 - 紫色气泡风格
    if (step.thought) {
        const thoughtBlock = document.createElement('div');
        thoughtBlock.className = 'trace-thought';
        thoughtBlock.innerHTML = `
            <div class="trace-thought-content">${escapeHtml(step.thought)}</div>
        `;
        stepDiv.appendChild(thoughtBlock);
    }

    // Action 块 - 橙色代码风格
    if (step.tool_calls && step.tool_calls.length > 0) {
        for (const call of step.tool_calls) {
            const actionBlock = document.createElement('div');
            actionBlock.className = 'trace-action';
            actionBlock.innerHTML = `
                <div class="trace-action-header">⚡ ${call.function.name}</div>
                <div class="trace-action-args">${escapeHtml(call.function.arguments)}</div>
            `;
            stepDiv.appendChild(actionBlock);
        }
    }

    // Observation 块 - 灰色终端风格
    if (step.tool_results && step.tool_results.length > 0) {
        for (const result of step.tool_results) {
            const success = result.success !== false;
            const obsBlock = document.createElement('div');
            obsBlock.className = 'trace-observation';
            obsBlock.innerHTML = `
                <div class="trace-observation-header">📟 ${success ? '观察结果' : '错误'}</div>
                <div class="trace-observation-content">${escapeHtml(result.output || result.error || JSON.stringify(result, null, 2))}</div>
            `;
            stepDiv.appendChild(obsBlock);
        }
    }

    // Final Response - 渲染到 Thought 块
    if (step.final_response) {
        const thoughtBlock = document.createElement('div');
        thoughtBlock.className = 'trace-thought';
        thoughtBlock.innerHTML = `
            <div class="trace-thought-content">${escapeHtml(step.final_response)}</div>
        `;
        stepDiv.appendChild(thoughtBlock);
    }

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
                            // 开始新步骤 - 创建 ReAct 步骤容器
                            currentStepDiv = document.createElement('div');
                            currentStepDiv.className = 'ReAct-step';
                            currentStepDiv.innerHTML = `
                                <div class="step-indicator">
                                    <span class="step-badge">${data.step}</span>
                                    <span>ReAct 步骤</span>
                                </div>
                                <div class="trace-thought" style="display:none;">
                                    <div class="trace-thought-content"></div>
                                </div>
                                <div class="trace-action" style="display:none;">
                                    <div class="trace-action-header"></div>
                                    <div class="trace-action-args"></div>
                                </div>
                                <div class="trace-observation" style="display:none;">
                                    <div class="trace-observation-header">📟 观察结果</div>
                                    <div class="trace-observation-content"></div>
                                </div>
                            `;
                            traceContent.appendChild(currentStepDiv);
                            break;

                        case 'thought':
                            // Thought 块 - 紫色气泡风格
                            if (currentStepDiv) {
                                const thoughtBlock = currentStepDiv.querySelector('.trace-thought');
                                if (thoughtBlock) {
                                    thoughtBlock.style.display = 'block';
                                    const contentDiv = thoughtBlock.querySelector('.trace-thought-content');
                                    if (contentDiv) contentDiv.textContent = content;
                                }
                            }
                            break;

                        case 'tool_call':
                            // Action 块 - 橙色代码风格
                            if (currentStepDiv) {
                                const actionBlock = currentStepDiv.querySelector('.trace-action');
                                if (actionBlock) {
                                    actionBlock.style.display = 'block';
                                    const header = actionBlock.querySelector('.trace-action-header');
                                    if (header) header.textContent = '⚡ ' + content;
                                }
                            }
                            break;

                        case 'tool_result':
                            // Observation 块 - 灰色终端风格
                            if (currentStepDiv) {
                                const obsBlock = currentStepDiv.querySelector('.trace-observation');
                                if (obsBlock) {
                                    obsBlock.style.display = 'block';
                                    const obsContent = obsBlock.querySelector('.trace-observation-content');
                                    if (obsContent) obsContent.textContent = content;
                                }
                            }
                            break;

                        case 'decision':
                            // Decision 块 - 绿色决策风格（循环终止逻辑）
                            if (currentStepDiv) {
                                const decisionBlock = document.createElement('div');
                                decisionBlock.className = 'trace-decision';
                                decisionBlock.innerHTML = `
                                    <div class="trace-decision-content">✨ ${escapeHtml(content)}</div>
                                `;
                                currentStepDiv.appendChild(decisionBlock);
                            }
                            break;

                        case 'final':
                            // 最终回复 - 更新到 Thought 块作为最终输出
                            finalResponse = content;
                            if (currentStepDiv) {
                                const thoughtBlock = currentStepDiv.querySelector('.trace-thought');
                                if (thoughtBlock) {
                                    thoughtBlock.style.display = 'block';
                                    const contentDiv = thoughtBlock.querySelector('.trace-thought-content');
                                    if (contentDiv) {
                                        contentDiv.textContent = content;
                                    }
                                    // 更新 Thought 标签
                                    thoughtBlock.querySelector('::before') // CSS 伪元素无法修改，用 style 代替
                                }
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
                saveConversationId(conversationId);
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
                saveConversationId(conversationId);
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
    clearStoredConversationId();
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

    // 从 localStorage 恢复会话 ID
    const storedConvId = loadConversationId();
    if (storedConvId) {
        conversationId = storedConvId;
        updateConversationIdDisplay(conversationId);

        // 加载并显示历史消息
        loadAndDisplayHistory(conversationId);
    } else {
        // 显示欢迎消息
        clearUI();
    }
}

/**
 * 加载并显示历史消息
 */
async function loadAndDisplayHistory(convId) {
    const messages = await loadConversationHistory(convId);

    if (messages.length > 0) {
        // 清空欢迎消息
        chatMessages.innerHTML = '';

        // 逐条显示历史消息
        for (const msg of messages) {
            addMessage(msg.role, msg.content);
        }

        // 清空 Trace
        traceContent.innerHTML = '';
    } else {
        clearUI();
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
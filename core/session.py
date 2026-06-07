# -*- coding: utf-8 -*-
"""
会话管理模块：session.py
=====================

本模块负责会话的持久化存储，使用 SQLite 数据库。

功能：
1. 创建新会话
2. 保存对话历史
3. 加载会话
4. 会话列表管理

设计理念：
    会话持久化使得服务重启后仍能恢复历史对话，
    提供更好的用户体验。
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


# =============================================================================
# 数据模型
# =============================================================================

@dataclass
class Session:
    """
    会话数据模型

    Attributes:
        id: 会话唯一标识符
        created_at: 创建时间
        updated_at: 最后更新时间
        messages: 对话历史列表
        metadata: 元数据（用户信息等）
    """
    id: str
    created_at: str
    updated_at: str
    messages: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Message:
    """
    消息数据模型

    Attributes:
        role: 角色（user/assistant/system）
        content:消息内容
        timestamp: 时间戳
    """
    role: str
    content: str
    timestamp: str = ""


# =============================================================================
# 会话管理器
# =============================================================================

class SessionManager:
    """
    会话管理器

    负责：
    1. 创建和管理会话数据库
    2. 保存和加载会话数据
    3. 会话列表查询

    使用 SQLite存储，无需额外服务。
    """

    def __init__(self, db_path: str = "sessions.db"):
        """
        初始化会话管理器

        Args:
            db_path: 数据库文件路径（相对或绝对路径）
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                messages TEXT NOT NULL,
                metadata TEXT NOT NULL
            )
        """)

        # Token 使用统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                prompt_tokens INTEGER NOT NULL,
                completion_tokens INTEGER NOT NULL,
                total_tokens INTEGER NOT NULL,
                model TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES sessions(id)
            )
        """)

        conn.commit()
        conn.close()

    def create_session(self, metadata: dict = None) -> Session:
        """
        创建新会话

        Args:
            metadata: 会话元数据（如用户信息等）

        Returns:
            新创建的 Session 对象
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        session = Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            messages=[],
            metadata=metadata or {}
        )

        self._save_session(session)
        return session

    def _save_session(self, session: Session):
        """保存会话到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO sessions (id, created_at, updated_at, messages, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session.id,
            session.created_at,
            session.updated_at,
            json.dumps(session.messages, ensure_ascii=False),
            json.dumps(session.metadata, ensure_ascii=False)
        ))

        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        根据 ID 获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Session 对象，如果不存在返回 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, created_at, updated_at, messages, metadata
            FROM sessions
            WHERE id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return Session(
            id=row[0],
            created_at=row[1],
            updated_at=row[2],
            messages=json.loads(row[3]),
            metadata=json.loads(row[4])
        )

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        向会话添加消息

        Args:
            session_id: 会话 ID
            role: 消息角色（user/assistant/system）
            content: 消息内容

        Returns:
            是否成功
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        session.messages.append(message)
        session.updated_at = datetime.now().isoformat()

        self._save_session(session)
        return True

    def update_messages(self, session_id: str, messages: list) -> bool:
        """
        更新会话的所有消息

        Args:
            session_id: 会话 ID
            messages: 新的消息列表

        Returns:
            是否成功
        """
        session = self.get_session(session_id)
        if session is None:
            return False

        session.messages = messages
        session.updated_at = datetime.now().isoformat()

        self._save_session(session)
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    def list_sessions(self, limit: int = 20, offset: int = 0) -> list[Session]:
        """
        获取会话列表

        Args:
            limit: 返回数量限制
            offset: 偏移量（用于分页）

        Returns:
            会话列表，按更新时间倒序排列
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, created_at, updated_at, messages, metadata
            FROM sessions
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [
            Session(
                id=row[0],
                created_at=row[1],
                updated_at=row[2],
                messages=json.loads(row[3]),
                metadata=json.loads(row[4])
            )
            for row in rows
        ]

    def get_conversation_context(self, session_id: str, max_messages: int = 10) -> list[dict]:
        """
        获取会话的对话上下文

        用于在继续对话时提供历史背景。

        Args:
            session_id: 会话 ID
            max_messages: 返回最近 N 条消息

        Returns:
            消息列表，每条消息包含 role 和 content
        """
        session = self.get_session(session_id)
        if session is None:
            return []

        # 返回最近的消息
        messages = session.messages[-max_messages:] if max_messages > 0 else session.messages

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

    def add_token_usage(
        self,
        conversation_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str
    ) -> bool:
        """
        记录 Token 使用统计

        Args:
            conversation_id: 会话 ID
            prompt_tokens: 提示词 token 数
            completion_tokens: 完成回复 token 数
            total_tokens: 总 token 数
            model: 使用的模型名称

        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO token_usage
                (conversation_id, timestamp, prompt_tokens, completion_tokens, total_tokens, model)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                datetime.now().isoformat(),
                prompt_tokens,
                completion_tokens,
                total_tokens,
                model
            ))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_token_stats(self, conversation_id: str) -> dict:
        """
        获取会话的 Token 统计信息

        Args:
            conversation_id: 会话 ID

        Returns:
            统计信息字典，包含累计和平均数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as call_count,
                SUM(prompt_tokens) as total_prompt,
                SUM(completion_tokens) as total_completion,
                SUM(total_tokens) as total_tokens,
                AVG(total_tokens) as avg_tokens
            FROM token_usage
            WHERE conversation_id = ?
        """, (conversation_id,))

        row = cursor.fetchone()
        conn.close()

        if row[0] == 0:
            return {
                "call_count": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "total_tokens": 0,
                "avg_tokens": 0
            }

        return {
            "call_count": row[0],
            "total_prompt_tokens": row[1] or 0,
            "total_completion_tokens": row[2] or 0,
            "total_tokens": row[3] or 0,
            "avg_tokens": round(row[4] or 0, 2)
        }


# =============================================================================
# 全局会话管理器实例
# =============================================================================

# 默认的会话管理器实例
_default_manager: Optional[SessionManager] = None


def get_session_manager(db_path: str = "sessions.db") -> SessionManager:
    """
    获取全局会话管理器实例（单例模式）

    Args:
        db_path: 数据库路径

    Returns:
        SessionManager 实例
    """
    global _default_manager

    if _default_manager is None:
        _default_manager = SessionManager(db_path)

    return _default_manager


def create_session(metadata: dict = None) -> Session:
    """便捷函数：创建新会话"""
    return get_session_manager().create_session(metadata)


def get_session(session_id: str) -> Optional[Session]:
    """便捷函数：获取会话"""
    return get_session_manager().get_session(session_id)


def add_message(session_id: str, role: str, content: str) -> bool:
    """便捷函数：添加消息"""
    return get_session_manager().add_message(session_id, role, content)


def update_messages(session_id: str, messages: list) -> bool:
    """便捷函数：更新消息"""
    return get_session_manager().update_messages(session_id, messages)


def get_conversation_context(session_id: str, max_messages: int = 10) -> list[dict]:
    """便捷函数：获取对话上下文"""
    return get_session_manager().get_conversation_context(session_id, max_messages)


def add_token_usage(
    conversation_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str
) -> bool:
    """便捷函数：记录 Token 使用统计"""
    return get_session_manager().add_token_usage(
        conversation_id, prompt_tokens, completion_tokens, total_tokens, model
    )


def get_token_stats(conversation_id: str) -> dict:
    """便捷函数：获取 Token 统计信息"""
    return get_session_manager().get_token_stats(conversation_id)
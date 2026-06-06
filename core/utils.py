# -*- coding: utf-8 -*-
"""
工具模块：utils.py
================

提供通用的工具函数和类：
1. 日志配置（loguru）
2. 重试装饰器（tenacity）
3. 其他通用工具

实验目的：
    统一日志格式和错误重试机制，提高系统可靠性。
"""

import sys
from pathlib import Path
from functools import wraps
from typing import Callable, Any

# =============================================================================
# 日志配置
# =============================================================================

def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> None:
    """
    配置 loguru 日志系统

    Args:
        log_dir: 日志目录路径
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR）

    使用方式：
        from core.utils import setup_logging
        setup_logging()
    """
    from loguru import logger
    import loguru

    # 移除默认的 handler
    logger.remove()

    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # 添加控制台输出
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # 添加文件输出（按日期分割）
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天零点轮转
        retention="7 days",  # 保留7天
        compression="zip",  # 压缩旧日志
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        encoding="utf-8"
    )

    # 添加错误日志单独输出
    logger.add(
        log_path / "error_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        encoding="utf-8"
    )

    logger.info(f"日志系统初始化完成，日志级别: {log_level}")


def get_logger(name: str = __name__):
    """
    获取 logger 实例

    Args:
        name: logger名称，通常使用模块名

    Returns:
        loguru.Logger 实例
    """
    from loguru import logger
    return logger.bind(name=name)


# =============================================================================
# 重试机制
# =============================================================================

def retry_on_error(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Callable[[Exception, int], None] = None
):
    """
    指数退避重试装饰器

    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        exponential_base: 指数基数
        exceptions: 需要重试的异常类型元组
        on_retry: 重试时的回调函数，参数为 (exception, attempt_number)

    使用方式：
        @retry_on_error(max_attempts=3, base_delay=1.0)
        def api_call():
            ...

    延迟时间计算：
        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
        第1次重试: 1s, 第2次: 2s, 第3次: 4s, ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            from loguru import logger
            import time

            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # 计算延迟时间（指数退避）
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

                        logger.warning(
                            f"{func.__name__} 第 {attempt} 次尝试失败: {e!s}, "
                            f"{delay:.1f}秒后重试..."
                        )

                        if on_retry:
                            on_retry(e, attempt)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} 达到最大重试次数 ({max_attempts}), 最终失败: {e!s}"
                        )

            # 所有尝试都失败后抛出异常
            raise last_exception

        return wrapper
    return decorator


class RetryConfig:
    """
    重试配置类

    统一管理重试参数，方便配置和管理。
    """
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def to_dict(self) -> dict:
        return {
            "max_attempts": self.max_attempts,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "exponential_base": self.exponential_base
        }


# LLM 调用重试配置（宽松一些）
LLM_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0
)

# 通用重试配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0
)


# =============================================================================
# 超时控制
# =============================================================================

def timeout(seconds: float):
    """
    函数超时装饰器

    Args:
        seconds: 超时时间（秒）

    注意：需要 signal 模块支持，Windows 下可能不完全支持

    使用方式：
        @timeout(30.0)
        def long_running_task():
            ...
    """
    import signal

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            def handler(signum, frame):
                raise TimeoutError(f"{func.__name__} 执行超时（{seconds}秒）")

            # 设置信号
            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(int(seconds))

            try:
                result = func(*args, **kwargs)
            finally:
                # 恢复信号
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)

            return result

        return wrapper
    return decorator


# =============================================================================
# 其他工具
# =============================================================================

def ensure_dir(path: str) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        Path 对象
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    安全解析 JSON，失败返回默认值

    Args:
        text: JSON 字符串
        default: 解析失败时返回的默认值

    Returns:
        解析后的对象或默认值
    """
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断过长的文本

    Args:
        text: 原文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
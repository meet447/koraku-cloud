"""Koraku — embeddable ReAct agent SDK and self-hostable assistant."""

from koraku.agent import Agent, AgentRunContext, ExecutionTarget
from koraku.core.config import Settings, configure, get_settings, use_settings
from koraku.core.auth import AuthResult, auth_error_detail, verify_request_auth
from koraku.core.models import AgentMessage, SessionState
from koraku.llm import UnifiedLLMClient
from koraku.sdk import Koraku, KorakuConfig
from koraku.tools import Tool, get_tool, get_tool_schemas
from koraku.tools.registry import AVAILABLE_TOOLS

__all__ = [
    "Agent",
    "AgentMessage",
    "AgentRunContext",
    "AuthResult",
    "AVAILABLE_TOOLS",
    "ExecutionTarget",
    "Koraku",
    "KorakuConfig",
    "SessionState",
    "Settings",
    "Tool",
    "UnifiedLLMClient",
    "auth_error_detail",
    "configure",
    "get_settings",
    "get_tool",
    "get_tool_schemas",
    "use_settings",
    "verify_request_auth",
]

__version__ = "0.2.0"

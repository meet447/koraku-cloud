"""Koraku — embeddable ReAct agent SDK and self-hostable assistant."""

from koraku.agent import Agent, AgentRunContext, ExecutionTarget
from koraku.core.config import Settings, configure, configure_sdk, get_settings, get_sdk_settings, use_settings
from koraku.core.sdk_settings import SdkSettings
from koraku.core.auth import AuthResult, auth_error_detail, verify_request_auth
from koraku.core.models import AgentMessage, SessionState
from koraku.llm import UnifiedLLMClient
from koraku.sdk import Koraku, KorakuConfig
from koraku.tools import Tool, get_tool, get_tool_schemas

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
    "SdkSettings",
    "configure",
    "configure_sdk",
    "get_settings",
    "get_sdk_settings",
    "get_tool",
    "get_tool_schemas",
    "use_settings",
    "verify_request_auth",
]

__version__ = "0.2.0"


def __getattr__(name: str):
    if name == "AVAILABLE_TOOLS":
        from koraku.tools.registry import available_tools

        return available_tools()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

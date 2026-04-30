from __future__ import annotations
from client.response import TokenUsage
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class AgentEventType(str,Enum):
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    AGENT_ERROR = "agent_error"

    TEXT_DELTA = "text_delta"
    TEXT_COMPLETE = "text_complete"
    
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TOOL_CONFIRMATION = "tool_confirmation"



@dataclass
class AgentEvent:
    type:AgentEventType
    data: dict[str,Any] = field(default_factory=dict)


    @classmethod
    def agent_start(cls,message:str) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_START,
            data={"message":message},
        )

    @classmethod
    def agent_end(cls,response:str | None = None,usage:TokenUsage | None = None) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_END,
            data={"response":response,"usage":usage.__dict__ if usage else None},
        )

    @classmethod
    def agent_error(cls,error:str,details:dict[str,Any] | None = None) -> AgentEvent:
        return cls(
            type=AgentEventType.AGENT_ERROR,
            data={"error":error,"details":details or {}},
        )

    @classmethod
    def text_delta(cls,content:str) -> AgentEvent:
        return cls(
            type=AgentEventType.TEXT_DELTA,
            data={"content":content},
        )

    @classmethod
    def text_complete(cls,content:str) -> AgentEvent:
        return cls(
            type=AgentEventType.TEXT_COMPLETE,
            data={"content":content},
        )

    @classmethod
    def tool_call(cls,name:str, arguments:dict) -> AgentEvent:
        return cls(
            type=AgentEventType.TOOL_CALL,
            data={"name":name, "arguments":arguments},
        )

    @classmethod
    def tool_result(cls,name:str, result:str, diff:str|None=None) -> AgentEvent:
        return cls(
            type=AgentEventType.TOOL_RESULT,
            data={"name":name, "result":result, "diff":diff},
        )

    @classmethod
    def tool_confirmation(cls, confirmation: Any) -> AgentEvent:
        return cls(
            type=AgentEventType.TOOL_CONFIRMATION,
            data={"confirmation": confirmation},
        )
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum



@dataclass
class TextDelta:
    content:str


    def __str__(self):
        return self.content


class StreamEventType(str,Enum):
    TEXT_DELTA="text_delta"
    MESSAGE_COMPLETION="message_completion"
    ERROR="error"
    TOOL_CALL="tool_call"
    
@dataclass
class TokenUsage:
    prompt_token: int =0
    completion_token: int =0
    total_token: int =0
    cached_token: int =0

    def __add__(self,other:TokenUsage):
        return TokenUsage(
            prompt_token=self.prompt_token + other.prompt_token,
            completion_token=self.completion_token + other.completion_token,
            total_token=self.total_token + other.total_token,
            cached_token=self.cached_token + other.cached_token,
        )
    


@dataclass
class StreamEvent:
    type:StreamEventType
    text_delta:TextDelta | None = None
    error:str | None = None
    finish_reason:str | None = None
    usage: TokenUsage | None = None
    tool_calls: list[dict] | None = None
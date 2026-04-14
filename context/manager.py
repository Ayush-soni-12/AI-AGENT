from dataclasses import dataclass
from prompt.system_prompt import get_system_prompt
from utils.text import count_tokens
from typing import Any


@dataclass
class MessageItem:
    role:str
    content:str
    token_count:str


class ContextManager:
    def __init__(self) -> None:
        self._system_prompt = get_system_prompt()
        self._model_name = "gemini-2.5-flash"
        self._messages:list[MessageItem] = []

    
    def add_user_message(self,content:str) -> None:
        item = MessageItem(
            role='user',
            content=content,
            token_count=count_tokens(self._model_name,content)
        )
        

        self._messages.append(item)

    
    def add_assistant_message(self,content:str) -> None:
        item = MessageItem(
            role='assistant',
            content=content,
            token_count=count_tokens(self._model_name,content)
        )

        self._messages.append(item)

    
    def get_messages(self) ->list[dict[str,Any]]:
        messages =[]

        if self._system_prompt:
            messages.append({
                "role":"system",
                "content":self._system_prompt
            })

        for item in self._messages:
            messages.append({
                "role":item.role,
                "content":item.content
            })

        return messages
        

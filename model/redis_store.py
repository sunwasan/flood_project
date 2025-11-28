from typing import List, Optional, Union, Literal, Dict, Any
from pydantic import BaseModel, Field

class MessageContent(BaseModel):
    id: str
    type: str
    content: str
    replytoken: str
    done: bool = False

class SingleUser(BaseModel):
    user_id: str
    messages: List[str]
    
class GroupUser(BaseModel):
    group_id: List[SingleUser]

class DatabaseModel(BaseModel):
    users: List[SingleUser]
    groups: List[GroupUser]
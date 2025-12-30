from pydantic import BaseModel
from typing import Optional

class UserLogin(BaseModel):
    email: str
    app_password: str
    openrouter_key: str

class AgentStatus(BaseModel):
    is_running: bool
    last_run: Optional[str] = None
    next_run: Optional[str] = None

from typing import Optional
from pydantic import BaseModel


class ProviderInfo(BaseModel):
    id: str
    name: str
    type: str  # "chat" or "embedding"
    description: Optional[str] = None
    configured: bool = False
    is_active: bool = True

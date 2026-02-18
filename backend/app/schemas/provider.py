from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ProviderInfo(BaseModel):
    id: str
    name: str
    type: str  # "chat" or "embedding"
    description: Optional[str] = None
    configured: bool = False
    is_active: bool = True
    supported_models: List[Dict[str, Any]] = []

"""
Token Schemas - Pydantic definitions for Authentication.
"""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    """
    OAuth2 Token Response.
    """

    access_token: str = Field(description="JWT Access Token")
    token_type: Literal["bearer"] = Field(default="bearer", description="Token Type (always 'bearer')")
    refresh_token: Optional[str] = Field(default=None, description="Refresh Token (optional)")


class TokenPayload(BaseModel):
    """
    JWT Token Payload (Claims).

    ARCHITECT NOTE: JWT Claims
    Standard claims:
    - sub (Subject): User ID
    - exp (Expiration): Timestamp
    - type: 'access' or 'refresh'
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sub: Optional[str] = Field(None, description="Subject (User ID)")
    exp: Optional[int] = Field(None, description="Expiration Timestamp")
    type: str = Field(default="access", description="Token usage scope")

    # Custom claims logic can serve here for validation if needed

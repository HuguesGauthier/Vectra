"""
Analytics Schemas.
"""

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsResponse(BaseModel):
    """
    Business Intelligence Metrics.
    """

    model_config = ConfigDict(from_attributes=True)

    total_docs: int = Field(default=0, description="Total documents ingested")
    total_vectors: int = Field(default=0, description="Total vector points stored")
    total_tokens: int = Field(default=0, description="Total tokens processed")
    estimated_cost: float = Field(default=0.0, description="Estimated cost in USD (based on current model pricing)")
    time_saved_hours: float = Field(default=0.0, description="Estimated manual labor hours saved")

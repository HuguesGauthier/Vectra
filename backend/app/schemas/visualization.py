from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Constants for DoS protection
MAX_TITLE_LENGTH = 200
MAX_AXIS_LABEL_LENGTH = 100
MAX_DATA_POINTS = 10000

# Allowed chart types
ALLOWED_CHART_TYPES = {"bar", "line", "pie", "treemap", "table"}


class ChartGeneration(BaseModel):
    """
    Schema for the generate_chart tool.
    Instructs the frontend to render a specific chart type with the provided data.
    """

    chart_type: Literal["bar", "line", "pie", "treemap", "table"] = Field(
        ..., description="Type of chart: 'bar', 'line', 'pie', 'treemap', 'table'. Use 'table' for text-heavy data."
    )
    title: str = Field(..., max_length=MAX_TITLE_LENGTH, description="A descriptive title for the chart.")
    data: List[Dict[str, Any]] = Field(
        ...,
        max_length=MAX_DATA_POINTS,
        description="List of data points. For 'bar'/'line', use [{'x': category, 'y': value}]. For 'pie', use [{'label': category, 'value': value}].",
    )
    x_axis: Optional[str] = Field(
        None, max_length=MAX_AXIS_LABEL_LENGTH, description="Label for the X-axis (if applicable)."
    )
    y_axis: Optional[str] = Field(
        None, max_length=MAX_AXIS_LABEL_LENGTH, description="Label for the Y-axis (if applicable)."
    )

    @field_validator("data")
    @classmethod
    def validate_data_not_empty(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure data is not empty."""
        if not v:
            raise ValueError("Data cannot be empty. At least one data point is required.")
        return v

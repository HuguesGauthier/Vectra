from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChartGeneration(BaseModel):
    """
    Schema for the generate_chart tool.
    Instructs the frontend to render a specific chart type with the provided data.
    """

    chart_type: str = Field(
        ..., description="Type of chart: 'bar', 'line', 'pie', 'treemap', 'table'. Use 'table' for text-heavy data."
    )
    title: str = Field(..., description="A descriptive title for the chart.")
    data: List[Dict[str, Any]] = Field(
        ...,
        description="List of data points. For 'bar'/'line', use [{'x': category, 'y': value}]. For 'pie', use [{'label': category, 'value': value}].",
    )
    x_axis: Optional[str] = Field(None, description="Label for the X-axis (if applicable).")
    y_axis: Optional[str] = Field(None, description="Label for the Y-axis (if applicable).")

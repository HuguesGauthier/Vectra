"""
Unit tests for backend/app/schemas/visualization.py
Tests cover chart type validation, DoS protection, and data validation.
"""

import pytest
from pydantic import ValidationError

from app.schemas.visualization import (
    ALLOWED_CHART_TYPES,
    MAX_AXIS_LABEL_LENGTH,
    MAX_DATA_POINTS,
    MAX_TITLE_LENGTH,
    ChartGeneration,
)


class TestChartGeneration:
    """Test ChartGeneration schema."""

    def test_valid_bar_chart(self):
        """Test creating a valid bar chart."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Sales by Region",
            data=[
                {"x": "North", "y": 100},
                {"x": "South", "y": 150},
                {"x": "East", "y": 200},
            ],
            x_axis="Region",
            y_axis="Sales",
        )
        assert chart.chart_type == "bar"
        assert chart.title == "Sales by Region"
        assert len(chart.data) == 3
        assert chart.x_axis == "Region"
        assert chart.y_axis == "Sales"

    def test_valid_line_chart(self):
        """Test creating a valid line chart."""
        chart = ChartGeneration(
            chart_type="line",
            title="Revenue Over Time",
            data=[
                {"x": "Q1", "y": 1000},
                {"x": "Q2", "y": 1500},
                {"x": "Q3", "y": 1200},
            ],
            x_axis="Quarter",
            y_axis="Revenue",
        )
        assert chart.chart_type == "line"

    def test_valid_pie_chart(self):
        """Test creating a valid pie chart."""
        chart = ChartGeneration(
            chart_type="pie",
            title="Market Share",
            data=[
                {"label": "Product A", "value": 40},
                {"label": "Product B", "value": 35},
                {"label": "Product C", "value": 25},
            ],
        )
        assert chart.chart_type == "pie"
        assert chart.x_axis is None
        assert chart.y_axis is None

    def test_valid_treemap_chart(self):
        """Test creating a valid treemap chart."""
        chart = ChartGeneration(
            chart_type="treemap",
            title="File System Usage",
            data=[
                {"name": "Documents", "size": 1000},
                {"name": "Images", "size": 2000},
            ],
        )
        assert chart.chart_type == "treemap"

    def test_valid_table(self):
        """Test creating a valid table."""
        chart = ChartGeneration(
            chart_type="table",
            title="User Data",
            data=[
                {"name": "Alice", "age": 30, "city": "NYC"},
                {"name": "Bob", "age": 25, "city": "LA"},
            ],
        )
        assert chart.chart_type == "table"


class TestChartTypeValidation:
    """Test chart type validation."""

    def test_all_allowed_chart_types_valid(self):
        """Test that all allowed chart types are accepted."""
        for chart_type in ALLOWED_CHART_TYPES:
            chart = ChartGeneration(
                chart_type=chart_type,  # type: ignore
                title="Test Chart",
                data=[{"x": 1, "y": 2}],
            )
            assert chart.chart_type == chart_type

    def test_invalid_chart_type_rejected(self):
        """Test that invalid chart types are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChartGeneration(
                chart_type="invalid_type",  # type: ignore
                title="Test",
                data=[{"x": 1, "y": 2}],
            )

        errors = exc_info.value.errors()
        assert any("chart_type" in str(error).lower() for error in errors)

    def test_empty_chart_type_rejected(self):
        """Test that empty chart types are rejected."""
        with pytest.raises(ValidationError):
            ChartGeneration(
                chart_type="",  # type: ignore
                title="Test",
                data=[{"x": 1, "y": 2}],
            )


class TestDoSProtection:
    """Test DoS protection via length limits."""

    def test_max_title_length_enforced(self):
        """Test that titles exceeding MAX_TITLE_LENGTH are rejected."""
        long_title = "x" * (MAX_TITLE_LENGTH + 1)
        with pytest.raises(ValidationError):
            ChartGeneration(
                chart_type="bar",
                title=long_title,
                data=[{"x": 1, "y": 2}],
            )

    def test_max_title_length_boundary(self):
        """Test that titles at exactly MAX_TITLE_LENGTH are accepted."""
        max_title = "x" * MAX_TITLE_LENGTH
        chart = ChartGeneration(
            chart_type="bar",
            title=max_title,
            data=[{"x": 1, "y": 2}],
        )
        assert len(chart.title) == MAX_TITLE_LENGTH

    def test_max_axis_label_length_enforced(self):
        """Test that axis labels exceeding MAX_AXIS_LABEL_LENGTH are rejected."""
        long_label = "x" * (MAX_AXIS_LABEL_LENGTH + 1)
        with pytest.raises(ValidationError):
            ChartGeneration(
                chart_type="bar",
                title="Test",
                data=[{"x": 1, "y": 2}],
                x_axis=long_label,
            )

    def test_max_data_points_enforced(self):
        """Test that data exceeding MAX_DATA_POINTS is rejected (DoS protection)."""
        large_data = [{"x": i, "y": i * 2} for i in range(MAX_DATA_POINTS + 1)]
        with pytest.raises(ValidationError):
            ChartGeneration(
                chart_type="bar",
                title="Test",
                data=large_data,
            )

    def test_max_data_points_boundary(self):
        """Test that data at exactly MAX_DATA_POINTS is accepted."""
        max_data = [{"x": i, "y": i * 2} for i in range(MAX_DATA_POINTS)]
        chart = ChartGeneration(
            chart_type="bar",
            title="Test",
            data=max_data,
        )
        assert len(chart.data) == MAX_DATA_POINTS


class TestDataValidation:
    """Test data validation rules."""

    def test_empty_data_rejected(self):
        """Test that empty data arrays are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChartGeneration(
                chart_type="bar",
                title="Test",
                data=[],
            )

        error_message = str(exc_info.value)
        assert "empty" in error_message.lower()

    def test_data_with_any_structure_accepted(self):
        """Test that data with any dict structure is accepted (flexible)."""
        # Bar chart structure
        chart1 = ChartGeneration(
            chart_type="bar",
            title="Test",
            data=[{"x": "A", "y": 10}],
        )
        assert chart1.data[0]["x"] == "A"

        # Pie chart structure
        chart2 = ChartGeneration(
            chart_type="pie",
            title="Test",
            data=[{"label": "A", "value": 10}],
        )
        assert chart2.data[0]["label"] == "A"

        # Custom structure (flexible)
        chart3 = ChartGeneration(
            chart_type="table",
            title="Test",
            data=[{"name": "Alice", "age": 30, "city": "NYC"}],
        )
        assert chart3.data[0]["name"] == "Alice"


class TestOptionalFields:
    """Test optional fields."""

    def test_axis_labels_optional(self):
        """Test that axis labels are optional."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Test",
            data=[{"x": 1, "y": 2}],
        )
        assert chart.x_axis is None
        assert chart.y_axis is None

    def test_only_x_axis_provided(self):
        """Test that only x_axis can be provided."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Test",
            data=[{"x": 1, "y": 2}],
            x_axis="Category",
        )
        assert chart.x_axis == "Category"
        assert chart.y_axis is None


class TestEdgeCases:
    """Test edge cases and production scenarios."""

    def test_unicode_in_title(self):
        """Test that Unicode characters in title are handled correctly."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Sales 世界 🌍",
            data=[{"x": 1, "y": 2}],
        )
        assert chart.title == "Sales 世界 🌍"

    def test_unicode_in_data(self):
        """Test that Unicode characters in data are handled correctly."""
        chart = ChartGeneration(
            chart_type="pie",
            title="Test",
            data=[{"label": "北京", "value": 100}],
        )
        assert chart.data[0]["label"] == "北京"

    def test_numeric_values_in_data(self):
        """Test that numeric values are preserved correctly."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Test",
            data=[{"x": "A", "y": 123.456}],
        )
        assert chart.data[0]["y"] == 123.456

    def test_nested_data_structure(self):
        """Test that nested data structures are accepted."""
        chart = ChartGeneration(
            chart_type="table",
            title="Test",
            data=[{"user": {"name": "Alice", "age": 30}, "score": 95}],
        )
        assert chart.data[0]["user"]["name"] == "Alice"

    def test_serialization_to_dict(self):
        """Test that charts can be serialized to dict (for API responses)."""
        chart = ChartGeneration(
            chart_type="bar",
            title="Test Chart",
            data=[{"x": "A", "y": 10}],
            x_axis="Category",
        )
        data = chart.model_dump()
        assert isinstance(data, dict)
        assert data["chart_type"] == "bar"
        assert data["title"] == "Test Chart"
        assert len(data["data"]) == 1


class TestConstants:
    """Test exported constants."""

    def test_allowed_chart_types_not_empty(self):
        """Test that ALLOWED_CHART_TYPES is not empty."""
        assert len(ALLOWED_CHART_TYPES) > 0

    def test_allowed_chart_types_contains_expected(self):
        """Test that ALLOWED_CHART_TYPES contains expected types."""
        expected_types = {"bar", "line", "pie", "table"}
        assert expected_types.issubset(ALLOWED_CHART_TYPES)

    def test_max_lengths_reasonable(self):
        """Test that max lengths are reasonable for production."""
        assert 50 <= MAX_TITLE_LENGTH <= 1000
        assert 20 <= MAX_AXIS_LABEL_LENGTH <= 500
        assert 100 <= MAX_DATA_POINTS <= 100000

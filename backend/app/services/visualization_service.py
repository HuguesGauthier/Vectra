import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.schemas.visualization import ChartGeneration
from app.services.chat.types import ChatContext
from app.services.chat.utils import LLMFactory

logger = logging.getLogger(__name__)

# --- Data Structures & Types ---


class VizDataInfo(BaseModel):
    """Normalized data structure extracted from any source."""

    row_count: int = 0
    columns: List[str] = Field(default_factory=list)
    sample_data: List[List[Any]] = Field(default_factory=list)
    has_numeric: bool = False
    is_currency: bool = False
    has_dates: bool = False
    has_categories: bool = False


class ChartData(BaseModel):
    """Structured Schema for LLM Extraction."""

    columns: List[str] = Field(description="2-3 column names, e.g. ['Fabricant', 'Prix']")
    rows: List[List[Union[str, float, int]]] = Field(
        description="Data rows. First column usually categorical, second numeric."
    )


class VisualizationService:
    """
    Service responsible for the "Heavy Lifting" of Visualization:
    1. Data Extraction (SQL, Regex, LLM Synthesis)
    2. Classification (Determining Chart Type)
    3. Formatting (Creating ApexCharts config)
    """

    async def extract_data_info(self, ctx: ChatContext) -> VizDataInfo:
        """Extracts structured data from Context (SQL, Vector, or Text)."""
        info = VizDataInfo()

        # Strategy 1: Raw SQL Result (Most Reliable - ZERO hallucination risk)
        if ctx.retrieved_sources:
            # Check for SQL metadata in sources
            for src in ctx.retrieved_sources:
                if src.get("metadata", {}).get("source_type") == "sql":
                    logger.info("⚡ Extraction Strategy: SQL Metadata detected")
                    # Usually we might parse the text or use sql_results if passed.
                    # Assuming ctx.sql_results is populated if SQL executed.
                    pass

        if getattr(ctx, "sql_results", None):
            logger.info(f"⚡ Extraction Strategy: SQL Raw ({len(ctx.sql_results)} rows)")
            return self._extract_from_sql(ctx)

        # Strategy 2: Virtual SQL (LLM Synthesis) for Vector Data
        # Trigger explicit request Check
        if self._is_explicit_chart_request(ctx.message) and ctx.retrieved_sources:
            logger.info("⚡ Extraction Strategy: Virtual SQL Synthesis (Explicit User Request)")
            synthesized = await self._synthesize_data_from_vector(ctx)
            if synthesized:
                return synthesized

        # Strategy 3: Regex Pattern Matching (Text Response)
        if ctx.full_response_text:
            logger.info("⚡ Extraction Strategy: Text Pattern Matching")
            parsed = await self._extract_from_text(ctx, ctx.full_response_text)
            if parsed.row_count > 0:
                logger.info(f"✅ Extracted {parsed.row_count} rows via Regex")
                return parsed

        return info

    async def classify_visualization_type(self, ctx: ChatContext, data: VizDataInfo) -> Tuple[str, Dict[str, int]]:
        """
        Determines the best chart type using AI analysis of user request and data.
        Returns: (viz_type_string, token_usage_dict)
        """
        tokens = {"input": 0, "output": 0}

        # 1. Intelligent Guard: Non-Numeric Data -> Force Table
        # This prevents "Bar Charts" for purely text data (e.g. "48 hours")
        if not data.has_numeric:
            logger.info("⚡ Classification Guard: No numeric data detected. Forcing 'table'.")
            return "table", tokens

        # 2. Heuristic: Very Large Datasets
        # Treemap for large datasets to avoid overcrowding
        if data.row_count > 20 and not data.has_dates:
            logger.info("⚡ Classification Heuristic: Treemap (Very Large Dataset, No Dates)")
            return "treemap", tokens

        # 3. AI Classification (Analyzes user request + data characteristics)
        logger.info("⚡ Classification: AI Analysis")
        return await self._classify_with_llm(ctx, data)

    def format_visualization_data(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Optional[Dict[str, Any]]:
        """Transforms normalized data into Frontend-ready JSON (ApexCharts/GenUI)."""
        logger.info(f"📊 format_visualization_data called with viz_type='{viz_type}'")

        # 1. Handle Table
        if viz_type == "table":
            return self._format_table(ctx, data)

        # 2. Handle Charts
        # Stacked Logic
        is_stacked = "stacked" in viz_type
        base_type = viz_type.replace("stacked_", "").replace("column", "bar")

        # Dispatcher based on Chart Family
        circular_types = ["pie", "donut", "polarArea", "radialBar"]
        hierarchical_types = ["treemap"]
        cartesian_types = ["bar", "line", "area", "radar", "scatter", "heatmap", "funnel", "slope"]

        if base_type in circular_types:
            return self._format_circular(ctx, base_type, data)

        if base_type in hierarchical_types:
            return self._format_hierarchical(ctx, base_type, data)

        if base_type in cartesian_types:
            return self._format_cartesian(ctx, base_type, data, stacked=is_stacked)

        logger.warning(f"Unknown visualization type: {viz_type}")

    def handle_chart_tool_call(self, tool_call: ChartGeneration) -> Optional[Dict[str, Any]]:
        """
        Adapts the LLM tool call output to the Frontend ApexCharts format.
        """
        logger.info(f"🎨 Visualization Tool Call: {tool_call.chart_type} - {tool_call.title}")

        # 1. Adapt ChartGeneration to VizDataInfo-like structure for reuse
        # Or simply map directly since we have explicit fields now.

        viz_type = tool_call.chart_type.lower()

        # Dispatcher
        if viz_type == "table":
            return self._format_table_tool(tool_call)

        # Map simple types
        circular_types = ["pie", "donut"]
        if viz_type in circular_types:
            return self._format_circular_tool(tool_call)

        # Cartesian
        return self._format_cartesian_tool(tool_call)

    def _format_table_tool(self, tool: ChartGeneration) -> Dict:
        # Infer columns from first data row if possible
        columns = []
        rows = []
        if tool.data:
            columns = list(tool.data[0].keys())
            rows = [list(d.values()) for d in tool.data]

        return {"viz_type": "table", "title": tool.title, "columns": columns, "rows": rows[:50]}

    def _format_circular_tool(self, tool: ChartGeneration) -> Dict:
        # Expects label/value or mapped
        labels = []
        series = []
        for d in tool.data:
            # Try common keys
            lbl = d.get("label") or d.get("x") or d.get("category") or list(d.values())[0]
            val = d.get("value") or d.get("y") or list(d.values())[1] if len(d) > 1 else 0

            labels.append(str(lbl))
            try:
                series.append(float(val))
            except:
                series.append(0)

        return {
            "viz_type": tool.chart_type,
            "title": tool.title,
            "labels": labels,
            "series": series,
            "chartOptions": {"labels": labels},
        }

    def _format_cartesian_tool(self, tool: ChartGeneration) -> Dict:
        # Expect x/y
        categories = []
        values = []

        for d in tool.data:
            cat = d.get(tool.x_axis) if tool.x_axis else (d.get("x") or d.get("category") or list(d.values())[0])
            val = (
                d.get(tool.y_axis)
                if tool.y_axis
                else (d.get("y") or d.get("value") or list(d.values())[1] if len(d) > 1 else 0)
            )

            categories.append(str(cat))
            try:
                values.append(float(val))
            except:
                values.append(0)

        return {
            "viz_type": tool.chart_type,  # bar, line, treemap
            "title": tool.title,
            "series": [{"name": tool.y_axis or "Value", "data": values}],
            "chartOptions": {"xaxis": {"categories": categories}},
        }

    # --- Legacy Methods (Kept for compatibility/fallback) ---

    def _extract_from_sql(self, ctx: ChatContext) -> VizDataInfo:
        info = VizDataInfo()

        if not ctx.sql_results:
            return info

        first_row = ctx.sql_results[0]

        # Scenario A: List of Dictionaries (Vanna/Pandas default)
        if isinstance(first_row, dict):
            info.columns = list(first_row.keys())
            # Extract values in stable order matching columns
            info.sample_data = [[str(row.get(col, "")) for col in info.columns] for row in ctx.sql_results]

        # Scenario B: List of Lists/Tuples (Raw Drivers)
        elif isinstance(first_row, (list, tuple)):
            info.sample_data = [[str(val) for val in row] for row in ctx.sql_results]
            # Cannot infer column names easily from raw tuples without metadata
            # heuristics below will handle it

        # Fallback
        else:
            info.sample_data = [[str(val) for val in row] for row in ctx.sql_results]

        info.row_count = len(ctx.sql_results)

        # Infer basic columns if missing (from Scenario B)
        if not info.columns and info.sample_data and len(info.sample_data[0]) >= 2:
            info.columns = ["Category", "Value"]

        # Detect Currency context from text
        if ctx.full_response_text and any(c in ctx.full_response_text for c in ["$", "€"]):
            info.is_currency = True
            info.has_numeric = True
        else:
            info.has_numeric = True  # SQL results usually imply numbers for charts

        return info

    def _detect_data_types(self, info: VizDataInfo) -> None:
        """Strictly validates if the dataset contains charting-compatible numeric values."""
        if not info.sample_data or len(info.sample_data) == 0:
            info.has_numeric = False
            return

        numeric_rows = 0
        total_rows = len(info.sample_data)

        # Heuristic: Check the last column (usually values) or second column
        target_col_idx = -1  # Default to last column
        if len(info.sample_data[0]) >= 2:
            target_col_idx = 1  # Second column often value

        for row in info.sample_data:
            if len(row) <= target_col_idx and target_col_idx != -1:
                continue

            val = row[target_col_idx]
            # If it's already a float/int, good.
            if isinstance(val, (int, float)):
                numeric_rows += 1
                continue

            # If string, try to parse
            if isinstance(val, str):
                # Clean currency/spaces
                clean = val.replace("$", "").replace("€", "").replace(" ", "").replace(",", "")
                try:
                    float(clean)
                    numeric_rows += 1
                except ValueError:
                    pass

        # Threshold: At least 50% of rows must be numeric to be considered a "Chart"
        info.has_numeric = (numeric_rows / total_rows) > 0.5
        if not info.has_numeric:
            logger.info(f"ℹ️ Type Detection: Data identified as TEXT ({numeric_rows}/{total_rows} numeric).")

    async def _extract_from_text(self, ctx: ChatContext, text: str) -> VizDataInfo:
        """Attempts to parse text using multiple regex strategies."""
        info = VizDataInfo()

        # P0: GenUI Table Extraction
        if ":::table" in text:
            logger.info("⚡ Extraction Strategy: GenUI Protocol (:::table)")
            # Simple Regex to extract JSON inside :::table { } :::
            # Fix: Allow optional closing tag to handle incomplete streams or missing closures
            match = re.search(r":::table\s*(\{[\s\S]*?)(?:::|$)", text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if "data" in data:
                        info.columns = [c.get("label", c.get("name")) for c in data.get("columns", [])]
                        # Normalize rows to list of lists
                        rows = []
                        for item in data["data"]:
                            if isinstance(item, dict):
                                row = [item.get(c.get("field") or c.get("name"), "") for c in data.get("columns", [])]
                                rows.append(row)
                        info.sample_data = rows
                        info.row_count = len(rows)

                        # Validate Types
                        self._detect_data_types(info)

                        if info.row_count > 0:
                            logger.info(f"✅ Extracted {info.row_count} rows via GenUI Protocol")
                        return info
                except Exception as e:
                    logger.warning(f"Failed to parse :::table JSON: {e}")

        # P1: Intelligent LLM Extraction (Replaces Regex)
        # If we didn't find a strict proto-table, but we have text that might contain data.
        logger.info("⚡ Extraction Strategy: Falling back to LLM Extraction")
        return await self._extract_with_llm(ctx, text)

    async def _synthesize_data_from_vector(self, ctx: ChatContext) -> Optional[VizDataInfo]:
        """Runs the LLM extraction chain to build a chart from unstructured text."""
        # Reuse module-level ChartData

        # Build Context
        context_text = ""
        for src in ctx.retrieved_sources[:15]:
            context_text += f"{src.get('text', '')[:1000]}\n"

        prompt = f"""Extract data for user query: "{ctx.message}"
        Output JSON matching ChartData schema.
        Context: {context_text[:10000]}
        """

        try:
            # Use centralized Factory
            from app.factories.chat_engine_factory import ChatEngineFactory

            llm = await ChatEngineFactory.create_from_assistant(
                ctx.assistant, ctx.settings_service, temperature=0, output_class=ChartData  # Enforce JSON schema
            )

            # Call LLM
            # Assuming llm.complete or similar returns strict JSON in text or obj
            # We use a wrapper usually. Logic here mimics original processor.
            response = await llm.acomplete(prompt)

            # Safe Parse
            txt = response.text if hasattr(response, "text") else str(response)
            txt = txt.replace("```json", "").replace("```", "")
            data_dict = json.loads(txt)
            chart_data = ChartData(**data_dict)

            info = VizDataInfo()
            info.columns = chart_data.columns
            info.sample_data = chart_data.rows
            info.row_count = len(chart_data.rows)
            info.has_numeric = True
            return info

        except Exception as e:
            logger.error(f"Virtual SQL Synthesis Error: {e}")
            return None

    async def _extract_with_llm(self, ctx: ChatContext, text: str) -> VizDataInfo:
        """Helper: Extract structured data from unstructured text using LLM."""
        info = VizDataInfo()

        # Fast exit if text is too short
        if len(text) < 50:
            return info

        prompt = f"""Extract data for chart from this text: 
        "{text[:2000]}"
        
        Output JSON matching ChartData schema.
        If no chartable data (numbers/categories), return empty rows.
        """

        try:
            # Use centralized Factory
            from app.factories.chat_engine_factory import ChatEngineFactory

            llm = await ChatEngineFactory.create_from_assistant(
                ctx.assistant, ctx.settings_service, temperature=0, output_class=ChartData
            )

            response = await llm.acomplete(prompt)

            # Safe Parse
            txt = response.text if hasattr(response, "text") else str(response)
            txt = txt.replace("```json", "").replace("```", "")

            if not txt.strip():
                return info  # Empty response

            data_dict = json.loads(txt)
            chart_data = ChartData(**data_dict)

            info.columns = chart_data.columns
            info.sample_data = chart_data.rows
            info.row_count = len(chart_data.rows)

            # Detect actual types instead of assuming
            self._detect_data_types(info)

            if info.row_count > 0:
                logger.info(f"✅ LLM Extraction Success: {info.row_count} rows")

            return info

        except Exception as e:
            logger.warning(f"LLM Extraction failed: {e}")
            return info

    # --- Private Helpers: Classification ---

    def _is_explicit_chart_request(self, message: str) -> bool:
        return self._check_explicit_request(message) is not None

    def _check_explicit_request(self, message: str) -> Optional[str]:
        msg = message.lower()

        # 1. Detect Stacked modifier
        is_stacked = "stacked" in msg or "empilé" in msg or "empile" in msg

        # 2. Map Base Types
        # IMPORTANT: More specific keywords MUST come BEFORE generic ones
        # e.g., "donut" before "pie" to avoid "donut" being caught by partial match
        map_types = {
            # Specific types first (to avoid substring conflicts)
            "donut": "donut",
            "beigne": "donut",
            "treemap": "treemap",
            "tree map": "treemap",
            "arborescence": "treemap",
            "heatmap": "heatmap",
            "heat map": "heatmap",
            "chaleur": "heatmap",
            "radialbar": "radialBar",
            "radial": "radialBar",
            "jauge": "radialBar",
            "gauge": "radialBar",
            "polararea": "polarArea",
            "polar": "polarArea",
            "polaire": "polarArea",
            # Generic types after
            "pie": "pie",
            "camembert": "pie",
            "secteur": "pie",
            "bar": "bar",
            "histogramme": "bar",
            "histo": "bar",
            "bâton": "bar",
            "line": "line",
            "courbe": "line",
            "evolution": "line",
            "area": "area",
            "aire": "area",
            "surface": "area",
            "radar": "radar",
            "araignée": "radar",
            "funnel": "funnel",
            "entonnoir": "funnel",
            "pyramide": "funnel",
            "scatter": "scatter",
            "nuage": "scatter",
            "dispersion": "scatter",
            "points": "scatter",
            "slope": "line",
            "pente": "line",
        }

        # Check all keywords in map_types
        # Sort by keyword length (longest first) to match most specific patterns first
        sorted_keywords = sorted(map_types.items(), key=lambda x: len(x[0]), reverse=True)

        for k, v in sorted_keywords:
            if k in msg:
                # If stacked and type supports stacking (bar, area, line), prepend
                if is_stacked and v in ["bar", "line", "area"]:
                    return f"stacked_{v}"
                return v

        return None

    async def _classify_with_llm(self, ctx: ChatContext, data: VizDataInfo) -> Tuple[str, Dict]:
        prompt = self._build_classification_prompt(ctx, data)
        try:
            from app.factories.chat_engine_factory import ChatEngineFactory

            llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, ctx.settings_service, temperature=0)

            response = await llm.acomplete(prompt)
            viz_type = self._parse_viz_type(str(response))

            # Extract real token usage from response
            tokens = {"input": 0, "output": 0}

            # Debug: Log response structure
            logger.debug(f"📊 VIZ Classification Response Type: {type(response)}")
            logger.debug(f"📊 Has 'raw' attr: {hasattr(response, 'raw')}")

            if hasattr(response, "raw") and response.raw:
                raw = response.raw
                logger.debug(f"📊 Raw response type: {type(raw)}")

                # Handle dict format (common with LlamaIndex)
                if isinstance(raw, dict):
                    logger.debug(f"📊 Raw dict keys: {list(raw.keys())}")

                    # Gemini format: usage_metadata in dict
                    if "usage_metadata" in raw:
                        usage = raw["usage_metadata"]
                        logger.debug(f"📊 Usage metadata dict: {usage}")
                        tokens = {
                            "input": usage.get("prompt_token_count", 0),
                            "output": usage.get("candidates_token_count", 0),
                        }
                        logger.info(
                            f"✅ Extracted tokens from dict['usage_metadata']: ↑{tokens['input']} ↓{tokens['output']}"
                        )
                    # OpenAI format: usage in dict
                    elif "usage" in raw:
                        usage = raw["usage"]
                        logger.debug(f"📊 Usage dict: {usage}")
                        tokens = {"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)}
                        logger.info(f"✅ Extracted tokens from dict['usage']: ↑{tokens['input']} ↓{tokens['output']}")
                    elif "token_usage" in raw:
                        usage = raw["token_usage"]
                        tokens = {
                            "input": usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0),
                            "output": usage.get("completion_tokens", 0) or usage.get("output_tokens", 0),
                        }
                        logger.info(
                            f"✅ Extracted tokens from dict['token_usage']: ↑{tokens['input']} ↓{tokens['output']}"
                        )
                    else:
                        logger.warning(f"⚠️ No usage key in dict. Keys: {list(raw.keys())}")

                # Handle object format with attributes
                elif hasattr(raw, "usage_metadata"):
                    usage = raw.usage_metadata
                    tokens = {
                        "input": getattr(usage, "prompt_token_count", 0),
                        "output": getattr(usage, "candidates_token_count", 0),
                    }
                    logger.info(f"✅ Extracted Gemini tokens: ↑{tokens['input']} ↓{tokens['output']}")
                elif hasattr(raw, "usage"):
                    usage = raw.usage
                    tokens = {
                        "input": getattr(usage, "prompt_tokens", 0),
                        "output": getattr(usage, "completion_tokens", 0),
                    }
                    logger.info(f"✅ Extracted OpenAI tokens: ↑{tokens['input']} ↓{tokens['output']}")
                else:
                    logger.warning(f"⚠️ No token usage found in response.raw")
            else:
                logger.warning(f"⚠️ Response has no 'raw' attribute. Type: {type(response)}")

            logger.info(f"📊 Classification result: {viz_type} | Tokens: ↑{tokens['input']} ↓{tokens['output']}")
            return viz_type, tokens

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "bar", {"input": 0, "output": 0}

    def _build_classification_prompt(self, ctx: ChatContext, data: VizDataInfo) -> str:
        # Build sample data preview
        sample_preview = ""
        if data.sample_data and len(data.sample_data) > 0:
            sample_preview = "\nFirst 3 rows:\n"
            for i, row in enumerate(data.sample_data[:3]):
                sample_preview += f"  {i+1}. {row}\n"

        return f"""You are a data visualization expert. Analyze the data and user request to select the BEST chart type.

USER REQUEST: "{ctx.message}"

DATA CHARACTERISTICS:
- Rows: {data.row_count}
- Columns: {data.columns}
- Has numeric values: {data.has_numeric}
- Has currency: {data.is_currency}
- Has dates/time: {data.has_dates}
{sample_preview}

AVAILABLE CHART TYPES:
1. **pie** - Shows parts of a whole (percentages, proportions). Best for 3-8 categories.
2. **donut** - Like pie but with center hole. More elegant for proportions. Best for 3-8 categories.
3. **bar** - Compare values across categories. Great for rankings, comparisons.
4. **line** - Show trends over time or continuous data. Best for time series.
5. **area** - Like line but filled. Emphasizes magnitude of change over time.
6. **treemap** - Hierarchical data or many categories (>12). Shows size proportions in rectangles.
7. **funnel** - Sequential process with decreasing values (sales pipeline, conversion rates).
8. **radar** - Compare multiple variables across categories. Spider web shape.
9. **table** - Raw data display when visualization doesn't add value.

SELECTION RULES:
- If user explicitly mentions a chart type (pie, donut, bar, etc.) → USE THAT
- Proportions/percentages of a whole → pie or donut
- Top N rankings/comparisons → bar
- Time series/trends → line or area  
- Many categories (>12) → treemap
- Sequential process/conversion funnel → funnel
- Multi-variable comparison → radar
- No numeric data → table

OUTPUT INSTRUCTIONS:
Respond with ONLY the chart type name (pie, donut, bar, line, area, treemap, funnel, radar, or table).
No explanation, just the type.
"""

    def _parse_viz_type(self, response: str) -> str:
        text = response.lower().strip()
        valid = [
            "table",
            "pie",
            "donut",
            "bar",
            "line",
            "treemap",
            "area",
            "radar",
            "funnel",
            "polarArea",
            "radialBar",
            "heatmap",
            "scatter",
        ]
        for v in valid:
            if v.lower() in text:
                return v
        return "bar"

    # --- Private Helpers: Formatting ---

    def _format_table(self, ctx: ChatContext, data: VizDataInfo) -> Dict:
        return {
            "viz_type": "table",
            "title": self._extract_title(data),
            "columns": data.columns,
            "rows": data.sample_data[:50],
        }

    def _format_circular(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Dict:
        labels = [str(r[0]) for r in data.sample_data[:15] if len(r) >= 1]
        values = []
        for r in data.sample_data[:15]:
            if len(r) >= 2:
                try:
                    values.append(float(r[1]))
                except:
                    values.append(0)
        return {
            "viz_type": viz_type,
            "title": self._extract_title(data),
            "labels": labels,
            "series": values,
            "is_currency": data.is_currency,
            "chart": {"type": viz_type},
            # Legacy/Fallback
            "chartOptions": {"chart": {"type": viz_type}, "labels": labels},
        }

    def _format_hierarchical(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Dict:
        data_points = []
        for r in data.sample_data[:30]:
            if len(r) >= 2:
                try:
                    data_points.append({"x": str(r[0]), "y": float(r[1])})
                except:
                    continue

        return {
            "viz_type": viz_type,
            "title": self._extract_title(data),
            "series": [{"data": data_points}],
            "chart": {"type": viz_type},
            "plotOptions": {"treemap": {"distributed": True}},
            # Legacy/Fallback
            "chartOptions": {"chart": {"type": viz_type}, "plotOptions": {"treemap": {"distributed": True}}},
        }

    def _format_cartesian(self, ctx: ChatContext, viz_type: str, data: VizDataInfo, stacked: bool) -> Dict:
        # 1. Extract Categories (Always Column 0)
        categories = [str(r[0]) for r in data.sample_data[:50] if len(r) >= 1]

        # 2. Extract Series (Columns 1...N)
        series_list = []

        # Determine how many value columns we have
        # We assume col 0 is category, so we look at col 1 onwards
        num_cols = 0
        if data.sample_data:
            num_cols = len(data.sample_data[0])

        if num_cols < 2:
            # Fallback for single column (unlikely but possible)
            series_list = [{"name": "Value", "data": [0] * len(categories)}]
        else:
            # Create a series for each value column
            for col_idx in range(1, num_cols):
                col_name = data.columns[col_idx] if col_idx < len(data.columns) else f"Series {col_idx}"

                # Extract values for this column
                # Handle missing/short rows gracefully
                viz_data = []
                for row in data.sample_data[:50]:
                    if len(row) > col_idx:
                        try:
                            val = float(row[col_idx])
                            viz_data.append(val)
                        except (ValueError, TypeError):
                            # Clean string if needed
                            if isinstance(row[col_idx], str):
                                clean = row[col_idx].replace(" ", "").replace("$", "").replace("€", "").replace(",", "")
                                try:
                                    viz_data.append(float(clean))
                                except:
                                    viz_data.append(0)
                            else:
                                viz_data.append(0)
                    else:
                        viz_data.append(0)

                series_list.append({"name": col_name, "data": viz_data})

        # Configure chart type and options
        final_type = viz_type
        extra_options = {}

        if viz_type == "funnel":
            logger.info("🎯 Funnel chart requested - using native ApexCharts funnel type")
            # For funnel, we typically only want ONE series (sorted).
            # If multiple exist, we take the first one or the one explicitly requested?
            # heuristic: take the first series only for funnel
            if len(series_list) > 1:
                series_list = [series_list[0]]

            extra_options = {
                "plotOptions": {"bar": {"horizontal": True, "isFunnel": True}},
                "dataLabels": {"enabled": True},
                "xaxis": {"categories": categories},
                "legend": {"show": False},
            }

        return {
            "viz_type": final_type,
            "title": self._extract_title(data),
            "series": series_list,
            "chartOptions": {"xaxis": {"categories": categories}, "chart": {"stacked": stacked}, **extra_options},
        }

    def _extract_title(self, data: VizDataInfo) -> str:
        if len(data.columns) >= 2:
            return f"{data.columns[1]} by {data.columns[0]}"
        return "Data Visualization"

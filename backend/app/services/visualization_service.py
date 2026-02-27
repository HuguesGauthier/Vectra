import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, Field

from app.factories.chat_engine_factory import ChatEngineFactory
from app.schemas.visualization import ChartGeneration
from app.services.chat.types import ChatContext

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
                logger.info(f"✅ Extracted {parsed.row_count} rows via Regex/Pattern")
                return parsed

        return info

    async def classify_visualization_type(self, ctx: ChatContext, data: VizDataInfo) -> Tuple[str, Dict[str, int]]:
        """
        Determines the best chart type using AI analysis of user request and data.
        Returns: (viz_type_string, token_usage_dict)
        """
        tokens = {"input": 0, "output": 0}

        # 1. Intelligent Guard: Non-Numeric Data -> Force Table
        if not data.has_numeric:
            logger.info("⚡ Classification Guard: No numeric data detected. Forcing 'table'.")
            return "table", tokens

        # 2. Heuristic: Very Large Datasets
        if data.row_count > 20 and not data.has_dates:
            logger.info("⚡ Classification Heuristic: Treemap (Very Large Dataset, No Dates)")
            return "treemap", tokens

        # 3. AI Classification
        logger.info("⚡ Classification: AI Analysis")
        return await self._classify_with_llm(ctx, data)

    def format_visualization_data(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Optional[Dict[str, Any]]:
        """Transforms normalized data into Frontend-ready JSON (ApexCharts/GenUI)."""
        logger.info(f"📊 format_visualization_data called with viz_type='{viz_type}'")

        if viz_type == "table":
            return self._format_table(ctx, data)

        is_stacked = "stacked" in viz_type
        base_type = viz_type.replace("stacked_", "").replace("column", "bar")

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
        return None

    def handle_chart_tool_call(self, tool_call: ChartGeneration) -> Optional[Dict[str, Any]]:
        """Adapts the LLM tool call output to the Frontend ApexCharts format."""
        logger.info(f"🎨 Visualization Tool Call: {tool_call.chart_type} - {tool_call.title}")

        viz_type = tool_call.chart_type.lower()

        if viz_type == "table":
            return self._format_table_tool(tool_call)

        circular_types = ["pie", "donut"]
        if viz_type in circular_types:
            return self._format_circular_tool(tool_call)

        return self._format_cartesian_tool(tool_call)

    def _format_table_tool(self, tool: ChartGeneration) -> Dict:
        columns = []
        rows = []
        if tool.data:
            columns = list(tool.data[0].keys())
            rows = [list(d.values()) for d in tool.data]

        return {"viz_type": "table", "title": tool.title, "columns": columns, "rows": rows[:50]}

    def _format_circular_tool(self, tool: ChartGeneration) -> Dict:
        labels = []
        series = []
        for d in tool.data:
            lbl = d.get("label") or d.get("x") or d.get("category") or list(d.values())[0]
            val = d.get("value") or d.get("y") or (list(d.values())[1] if len(d) > 1 else 0)

            labels.append(str(lbl))
            try:
                series.append(float(val))
            except (ValueError, TypeError):
                series.append(0)

        return {
            "viz_type": tool.chart_type,
            "title": tool.title,
            "labels": labels,
            "series": series,
            "chartOptions": {"labels": labels},
        }

    def _format_cartesian_tool(self, tool: ChartGeneration) -> Dict:
        categories = []
        values = []

        for d in tool.data:
            cat = d.get(tool.x_axis) if tool.x_axis else (d.get("x") or d.get("category") or list(d.values())[0])
            val = (
                d.get(tool.y_axis)
                if tool.y_axis
                else (d.get("y") or d.get("value") or (list(d.values())[1] if len(d) > 1 else 0))
            )

            categories.append(str(cat))
            try:
                values.append(float(val))
            except (ValueError, TypeError):
                values.append(0)

        return {
            "viz_type": tool.chart_type,
            "title": tool.title,
            "series": [{"name": tool.y_axis or "Value", "data": values}],
            "chartOptions": {"xaxis": {"categories": categories}},
        }

    def _extract_from_sql(self, ctx: ChatContext) -> VizDataInfo:
        info = VizDataInfo()
        if not ctx.sql_results:
            return info

        first_row = ctx.sql_results[0]

        if isinstance(first_row, dict):
            info.columns = list(first_row.keys())
            info.sample_data = [[row.get(col, "") for col in info.columns] for row in ctx.sql_results]
        elif isinstance(first_row, (list, tuple)):
            info.sample_data = [list(row) for row in ctx.sql_results]
        else:
            info.sample_data = [list(row) if hasattr(row, "__iter__") else [row] for row in ctx.sql_results]

        info.row_count = len(ctx.sql_results)

        if not info.columns and info.sample_data and len(info.sample_data[0]) >= 2:
            info.columns = ["Category", "Value"]

        # Final pass on types
        self._detect_data_types(info)

        # Infer Currency from text context if not already detected
        if not info.is_currency and ctx.full_response_text:
            if any(c in ctx.full_response_text for c in ["$", "€", " CAD", " USD"]):
                info.is_currency = True

        return info

    def _detect_data_types(self, info: VizDataInfo) -> None:
        """Strictly validates if the dataset contains charting-compatible numeric values."""
        if not info.sample_data:
            info.has_numeric = False
            return

        numeric_rows = 0
        total_rows = len(info.sample_data)
        target_col_idx = 1 if len(info.sample_data[0]) >= 2 else -1

        for row in info.sample_data:
            if target_col_idx == -1 or len(row) <= target_col_idx:
                continue

            val = row[target_col_idx]
            if isinstance(val, (int, float)):
                numeric_rows += 1
                continue

            if isinstance(val, str):
                # Robust cleaning for currency and international numbers
                clean = val.replace("$", "").replace("€", "").replace(" ", "").replace("\xa0", "").replace(",", "")
                if "." in val and "," not in val:  # US style 1,000.00 -> 1000.00
                    pass
                elif "," in val and "." not in val:  # FR style 1 000,00 -> 1000.00
                    clean = val.replace(" ", "").replace("\xa0", "").replace(",", ".")

                try:
                    float(clean)
                    numeric_rows += 1
                except ValueError:
                    pass

        info.has_numeric = (numeric_rows / total_rows) > 0.5 if total_rows > 0 else False

    async def _extract_from_text(self, ctx: ChatContext, text: str) -> VizDataInfo:
        """Attempts to parse text using multiple regex strategies."""
        info = VizDataInfo()

        # GenUI Table Extraction
        if ":::table" in text:
            logger.info("⚡ Extraction Strategy: GenUI Protocol (:::table)")
            match = re.search(r":::table\s*(\{[\s\S]*?)(?:::|$)", text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if "data" in data:
                        cols = data.get("columns", [])
                        info.columns = [c.get("label", c.get("name", "")) for c in cols]
                        rows = []
                        for item in data["data"]:
                            if isinstance(item, dict):
                                row = [item.get(c.get("field") or c.get("name"), "") for c in cols]
                                rows.append(row)
                        info.sample_data = rows
                        info.row_count = len(rows)
                        self._detect_data_types(info)
                        return info
                except Exception as e:
                    logger.warning(f"Failed to parse :::table JSON: {e}")

        # Intelligent LLM Extraction fallback
        logger.info("⚡ Extraction Strategy: Falling back to LLM Extraction")
        return await self._extract_with_llm(ctx, text)

    async def _synthesize_data_from_vector(self, ctx: ChatContext) -> Optional[VizDataInfo]:
        """Runs the LLM extraction chain to build a chart from unstructured text."""
        context_text = "\n".join([src.get("text", "")[:1000] for src in ctx.retrieved_sources[:15]])

        prompt = f"""Extract data for user query: "{ctx.message}"
        Output JSON matching ChartData schema.
        Context: {context_text[:10000]}
        """

        try:
            llm = await ChatEngineFactory.create_from_assistant(
                ctx.assistant, ctx.settings_service, temperature=0, output_class=ChartData
            )
            response = await llm.acomplete(prompt)
            txt = response.text if hasattr(response, "text") else str(response)
            txt = txt.replace("```json", "").replace("```", "").strip()

            data_dict = json.loads(txt)
            chart_data = ChartData(**data_dict)

            info = VizDataInfo(
                columns=chart_data.columns,
                sample_data=chart_data.rows,
                row_count=len(chart_data.rows),
                has_numeric=True,
            )
            return info
        except Exception as e:
            logger.error(f"Virtual SQL Synthesis Error: {e}")
            return None

    async def _extract_with_llm(self, ctx: ChatContext, text: str) -> VizDataInfo:
        """Helper: Extract structured data from unstructured text using LLM."""
        info = VizDataInfo()
        if len(text) < 50:
            return info

        prompt = f"""Extract data for chart from this text: 
        "{text[:2000]}"
        Output JSON matching ChartData schema. If no chartable data, return empty rows.
        """

        try:
            llm = await ChatEngineFactory.create_from_assistant(
                ctx.assistant, ctx.settings_service, temperature=0, output_class=ChartData
            )
            response = await llm.acomplete(prompt)
            txt = response.text if hasattr(response, "text") else str(response)
            txt = txt.replace("```json", "").replace("```", "").strip()

            if not txt:
                return info

            data_dict = json.loads(txt)
            chart_data = ChartData(**data_dict)

            info.columns = chart_data.columns
            info.sample_data = chart_data.rows
            info.row_count = len(chart_data.rows)
            self._detect_data_types(info)
            return info
        except Exception as e:
            logger.warning(f"LLM Extraction failed: {e}")
            return info

    def _is_explicit_chart_request(self, message: str) -> bool:
        return self._check_explicit_request(message) is not None

    def _check_explicit_request(self, message: str) -> Optional[str]:
        msg = message.lower()
        is_stacked = any(k in msg for k in ["stacked", "empilé", "empile"])

        map_types = {
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

        sorted_keywords = sorted(map_types.items(), key=lambda x: len(x[0]), reverse=True)
        for k, v in sorted_keywords:
            if k in msg:
                if is_stacked and v in ["bar", "line", "area"]:
                    return f"stacked_{v}"
                return v
        return None

    async def _classify_with_llm(self, ctx: ChatContext, data: VizDataInfo) -> Tuple[str, Dict]:
        prompt = self._build_classification_prompt(ctx, data)
        try:
            llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, ctx.settings_service, temperature=0)
            response = await llm.acomplete(prompt)
            viz_type = self._parse_viz_type(str(response))

            # Helper for token extraction
            tokens = self._extract_tokens(response)
            logger.info(f"📊 Classification result: {viz_type} | Tokens: ↑{tokens['input']} ↓{tokens['output']}")
            return viz_type, tokens
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "bar", {"input": 0, "output": 0}

    def _extract_tokens(self, response: Any) -> Dict[str, int]:
        """Centralized logic to extract tokens from various LLM response formats."""
        tokens = {"input": 0, "output": 0}
        if not hasattr(response, "raw") or not response.raw:
            return tokens

        raw = response.raw
        try:
            if isinstance(raw, dict):
                if "usage_metadata" in raw:
                    u = raw["usage_metadata"]
                    tokens["input"] = u.get("prompt_token_count", 0)
                    tokens["output"] = u.get("candidates_token_count", 0)
                elif "usage" in raw:
                    u = raw["usage"]
                    tokens["input"] = u.get("prompt_tokens", 0)
                    tokens["output"] = u.get("completion_tokens", 0)
                elif "token_usage" in raw:
                    u = raw["token_usage"]
                    tokens["input"] = u.get("prompt_tokens", 0) or u.get("input_tokens", 0)
                    tokens["output"] = u.get("completion_tokens", 0) or u.get("output_tokens", 0)
            elif hasattr(raw, "usage_metadata"):
                u = raw.usage_metadata
                tokens["input"] = getattr(u, "prompt_token_count", 0)
                tokens["output"] = getattr(u, "candidates_token_count", 0)
            elif hasattr(raw, "usage"):
                u = raw.usage
                tokens["input"] = getattr(u, "prompt_tokens", 0)
                tokens["output"] = getattr(u, "completion_tokens", 0)
        except Exception as e:
            logger.warning(f"Token extraction error: {e}")
        return tokens

    def _build_classification_prompt(self, ctx: ChatContext, data: VizDataInfo) -> str:
        sample = ""
        if data.sample_data:
            sample = "\nFirst 3 rows:\n" + "\n".join([f"  {i+1}. {r}" for i, r in enumerate(data.sample_data[:3])])

        return f"""You are a data visualization expert. Analyze the data and user request to select the BEST chart type.

USER REQUEST: "{ctx.message}"
DATA: Rows={data.row_count}, Columns={data.columns}, Numeric={data.has_numeric}, Currency={data.is_currency}, Dates={data.has_dates}
{sample}

AVAILABLE: pie, donut, bar, line, area, treemap, funnel, radar, table.
RULES:
- Explicit mention → USE THAT
- Proportions/Parts of whole → pie/donut
- Rankings/Comparisons → bar
- Trends over time → line/area
- Large datasets (>12) → treemap
- Sequential process → funnel
- No numeric data → table

Respond with ONLY the chart type name.
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
            "polararea",
            "radialbar",
            "heatmap",
            "scatter",
        ]
        for v in valid:
            if v.lower() in text:
                return v
        return "bar"

    def _format_table(self, ctx: ChatContext, data: VizDataInfo) -> Dict:
        return {
            "viz_type": "table",
            "title": self._extract_title(data),
            "columns": data.columns,
            "rows": data.sample_data[:50],
        }

    def _format_circular(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Dict:
        labels = [str(r[0]) for r in data.sample_data[:15] if r]
        values = []
        for r in data.sample_data[:15]:
            if len(r) >= 2:
                val = r[1]
                if isinstance(val, (int, float)):
                    values.append(float(val))
                elif isinstance(val, str):
                    # Robust cleaning
                    clean = val.replace("$", "").replace("€", "").replace(" ", "").replace("\xa0", "").replace(",", "")
                    if "," in val and "." not in val:
                        clean = val.replace(" ", "").replace("\xa0", "").replace(",", ".")
                    try:
                        values.append(float(clean))
                    except (ValueError, TypeError):
                        values.append(0)
                else:
                    values.append(0)
        return {
            "viz_type": viz_type,
            "title": self._extract_title(data),
            "labels": labels,
            "series": values,
            "is_currency": data.is_currency,
            "chartOptions": {"labels": labels},
        }

    def _format_hierarchical(self, ctx: ChatContext, viz_type: str, data: VizDataInfo) -> Dict:
        points = []
        for r in data.sample_data[:30]:
            if len(r) >= 2:
                try:
                    points.append({"x": str(r[0]), "y": float(r[1])})
                except (ValueError, TypeError):
                    continue
        return {
            "viz_type": viz_type,
            "title": self._extract_title(data),
            "series": [{"data": points}],
            "chartOptions": {"plotOptions": {"treemap": {"distributed": True}}},
        }

    def _format_cartesian(self, ctx: ChatContext, viz_type: str, data: VizDataInfo, stacked: bool) -> Dict:
        categories = [str(r[0]) for r in data.sample_data[:50] if r]
        series_list = []
        num_cols = len(data.sample_data[0]) if data.sample_data else 0

        if num_cols < 2:
            series_list = [{"name": "Value", "data": [0] * len(categories)}]
        else:
            for col_idx in range(1, num_cols):
                name = data.columns[col_idx] if col_idx < len(data.columns) else f"Series {col_idx}"
                vals = []
                for r in data.sample_data[:50]:
                    val = 0
                    if len(r) > col_idx:
                        v = r[col_idx]
                        if isinstance(v, (int, float)):
                            val = v
                        elif isinstance(v, str):
                            try:
                                val = float(v.replace(" ", "").replace("$", "").replace("€", "").replace(",", ""))
                            except ValueError:
                                pass
                    vals.append(val)
                series_list.append({"name": name, "data": vals})

        options = {"xaxis": {"categories": categories}, "chart": {"stacked": stacked}}
        if viz_type == "funnel":
            if series_list:
                series_list = [series_list[0]]
            options["plotOptions"] = {"bar": {"horizontal": True, "isFunnel": True}}
            options["legend"] = {"show": False}

        return {
            "viz_type": viz_type,
            "title": self._extract_title(data),
            "series": series_list,
            "chartOptions": options,
        }

    def _extract_title(self, data: VizDataInfo) -> str:
        if len(data.columns) >= 2:
            return f"{data.columns[1]} by {data.columns[0]}"
        return "Data Visualization"

"""
Centralized catalog of supported AI models per provider.

This is the SINGLE SOURCE OF TRUTH for available models AND their pricing.
When a model is added, deprecated, or removed, update ONLY this file.

Each model entry contains:
- id: API identifier used in requests
- name: Human-readable display name
- description: Short description of capabilities
- category: "flagship" | "balanced" | "economy" | "reasoning"
- input_price: Cost per 1M input tokens (USD)
- output_price: Cost per 1M output tokens (USD)
"""

from typing import Any, Dict, Optional, Tuple

ModelEntry = dict[str, Any]

# ---------------------------------------------------------------------------
#  Chat Models
# ---------------------------------------------------------------------------
SUPPORTED_CHAT_MODELS: dict[str, list[ModelEntry]] = {
    "gemini": [
        # ── Flagship ──
        {
            "id": "gemini-3-pro-preview",
            "name": "Gemini 3 Pro Preview",
            "description": "Our most powerful frontier model. Superior reasoning, coding, and complex task handling with massive context.",
            "category": "flagship",
            "input_price": 2.00,
            "output_price": 12.00,
        },
        {
            "id": "gemini-2.5-pro",
            "name": "Gemini 2.5 Pro",
            "description": "Premium flagship model. Optimized for high-level reasoning and deep document analysis.",
            "category": "flagship",
            "input_price": 1.25,
            "output_price": 10.00,
        },
        # ── Balanced ──
        {
            "id": "gemini-3-flash-preview",
            "name": "Gemini 3 Flash Preview",
            "description": "Next-gen efficiency. Ultra-fast responses with GPT-4 class intelligence.",
            "category": "balanced",
            "input_price": 0.50,
            "output_price": 3.00,
        },
        {
            "id": "gemini-2.5-flash",
            "name": "Gemini 2.5 Flash",
            "description": "The perfect all-rounder. Fast, reliable, and capable for most production tasks.",
            "category": "balanced",
            "input_price": 0.30,
            "output_price": 2.50,
        },
        # ── Economy ──
        {
            "id": "gemini-2.5-flash-lite",
            "name": "Gemini 2.5 Flash-Lite",
            "description": "High-efficiency 2.5 model. Optimized for speed and massive volume at low cost.",
            "category": "economy",
            "input_price": 0.10,
            "output_price": 0.40,
        },
        {
            "id": "gemini-2.0-flash",
            "name": "Gemini 2.0 Flash",
            "description": "Industry-leading speed. Incredible performance with near-instant responses.",
            "category": "economy",
            "input_price": 0.10,
            "output_price": 0.40,
        },
        {
            "id": "gemini-2.0-flash-lite",
            "name": "Gemini 2.0 Flash-Lite",
            "description": "Our most cost-effective model ever. Built for massive scale without sacrificing core logic.",
            "category": "economy",
            "input_price": 0.075,
            "output_price": 0.30,
        },
    ],
    "openai": [
        # ── Flagship ──
        {
            "id": "gpt-5.2",
            "name": "GPT-5.2 (Flagship)",
            "description": "Latest flagship model. Enhanced reasoning and multimodal capabilities with 128k-400k context.",
            "category": "flagship",
            "input_price": 1.75,
            "output_price": 14.00,
        },
        {
            "id": "gpt-5.2-pro",
            "name": "GPT-5.2 Pro",
            "description": "Smartest and most precise model. Ideal for complex coding and deep analysis.",
            "category": "flagship",
            "input_price": 21.00,
            "output_price": 168.00,
        },
        {
            "id": "gpt-5.1",
            "name": "GPT-5.1",
            "description": "Highly capable frontier model with improved stability and performance.",
            "category": "flagship",
            "input_price": 1.25,
            "output_price": 10.00,
        },
        {
            "id": "gpt-5",
            "name": "GPT-5 (Base)",
            "description": "Foundation model for the GPT-5 generation. State-of-the-art general intelligence.",
            "category": "flagship",
            "input_price": 1.25,
            "output_price": 10.00,
        },
        # ── Reasoning ──
        {
            "id": "o1",
            "name": "OpenAI o1",
            "description": "Advanced reasoning model for complex logical tasks and scientific problem solving.",
            "category": "reasoning",
            "input_price": 15.00,
            "output_price": 60.00,
        },
        {
            "id": "o3",
            "name": "OpenAI o3",
            "description": "Next-gen reasoning model. Superior performance in logic, math, and coding.",
            "category": "reasoning",
            "input_price": 2.00,
            "output_price": 8.00,
        },
        {
            "id": "o3-mini",
            "name": "OpenAI o3-mini",
            "description": "Compact reasoning model. Fast and efficient for logic-heavy workloads.",
            "category": "reasoning",
            "input_price": 1.10,
            "output_price": 4.40,
        },
        {
            "id": "o4-mini",
            "name": "OpenAI o4-mini",
            "description": "Latest affordable reasoning model. Optimized for analytical efficiency.",
            "category": "reasoning",
            "input_price": 1.10,
            "output_price": 4.40,
        },
        # ── Balanced ──
        {
            "id": "gpt-5-mini",
            "name": "GPT-5 Mini",
            "description": "Balanced performance and cost for the GPT-5 generation.",
            "category": "balanced",
            "input_price": 0.25,
            "output_price": 2.00,
        },
        {
            "id": "gpt-4.1-mini",
            "name": "GPT-4.1 Mini",
            "description": "Reliable and efficient model for production applications.",
            "category": "balanced",
            "input_price": 0.40,
            "output_price": 1.60,
        },
        # ── Economy ──
        {
            "id": "gpt-5-nano",
            "name": "GPT-5 Nano",
            "description": "Ultra-fast and affordable model for high-throughput, simple tasks.",
            "category": "economy",
            "input_price": 0.05,
            "output_price": 0.40,
        },
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
            "description": "Legacy balanced/economy model. Widely compatible and cost-effective.",
            "category": "economy",
            "input_price": 0.15,
            "output_price": 0.60,
        },
    ],
    "mistral": [
        # ── General Purpose ──
        {
            "id": "mistral-large-latest",
            "name": "Mistral Large 3 (Flagship)",
            "description": "Mistral's top-tier model. Best for complex reasoning, multi-step tasks, and high-precision coding.",
            "category": "flagship",
            "input_price": 2.00,
            "output_price": 6.00,
        },
        {
            "id": "mistral-medium-latest",
            "name": "Mistral Medium 3",
            "description": "High-performance model with optimized cost for professional applications.",
            "category": "balanced",
            "input_price": 0.10,
            "output_price": 0.30,
        },
        {
            "id": "mistral-small-latest",
            "name": "Mistral Small 3.1",
            "description": "Fast and efficient model with 128k context. Ideal for routine tasks.",
            "category": "balanced",
            "input_price": 0.10,
            "output_price": 0.30,
        },
        {
            "id": "open-mistral-nemo",
            "name": "Mistral NeMo",
            "description": "Efficient 12B model developed with NVIDIA. Excellent for edge and specialized use.",
            "category": "economy",
            "input_price": 0.15,
            "output_price": 0.15,
        },
        {
            "id": "mistral-tiny",
            "name": "Mistral Tiny",
            "description": "Lightest Mistral model for simple classification and low-latency responses.",
            "category": "economy",
            "input_price": 0.25,
            "output_price": 0.25,
        },
        # ── Edge Optimized (Ministral) ──
        {
            "id": "ministral-3b-latest",
            "name": "Ministral 3 3B",
            "description": "Ultra-compact model for edge computing and mobile devices.",
            "category": "economy",
            "input_price": 0.10,
            "output_price": 0.10,
        },
        {
            "id": "ministral-8b-latest",
            "name": "Ministral 3 8B",
            "description": "Balanced edge model with stronger reasoning capabilities.",
            "category": "economy",
            "input_price": 0.15,
            "output_price": 0.15,
        },
        {
            "id": "ministral-14b-latest",
            "name": "Ministral 3 14B",
            "description": "Highest capacity edge model for complex processing in constrained environments.",
            "category": "economy",
            "input_price": 0.20,
            "output_price": 0.20,
        },
        # ── Specialized ──
        {
            "id": "codestral-latest",
            "name": "Codestral 22B (Coding)",
            "description": "Top-tier code generation model supporting 80+ programming languages.",
            "category": "balanced",
            "input_price": 1.00,
            "output_price": 3.00,
        },
        {
            "id": "pixtral-large-latest",
            "name": "Pixtral Large (Vision)",
            "description": "State-of-the-art multimodal vision model for documents and complex image analysis.",
            "category": "flagship",
            "input_price": 2.00,
            "output_price": 6.00,
        },
        {
            "id": "pixtral-12b-2409",
            "name": "Pixtral 12B",
            "description": "Efficient multimodal model for general vision tasks.",
            "category": "balanced",
            "input_price": 0.15,
            "output_price": 0.15,
        },
        {
            "id": "voxtral-latest",
            "name": "Voxtral (Audio)",
            "description": "Specialized audio understanding and speech processing model.",
            "category": "balanced",
            "input_price": 0.10,
            "output_price": 0.30,
        },
        # ── Research and Free ──
        {
            "id": "devstral-latest",
            "name": "Devstral",
            "description": "Experimental model optimized for software developer agents.",
            "category": "economy",
            "input_price": 0.00,
            "output_price": 0.00,
        },
        {
            "id": "open-mistral-7b",
            "name": "Mistral 7B v0.3",
            "description": "The original classic 7B model. Fast and reliable.",
            "category": "economy",
            "input_price": 0.25,
            "output_price": 0.25,
        },
    ],
    "anthropic": [
        # ── Flagship ──
        {
            "id": "claude-3-opus-latest",
            "name": "Claude 3.5 Opus (Flagship)",
            "description": "Powerful model for highly complex tasks. Excellent for analysis and multi-step reasoning.",
            "category": "flagship",
            "input_price": 15.00,
            "output_price": 75.00,
        },
        # ── Balanced ──
        {
            "id": "claude-3-7-sonnet-latest",
            "name": "Claude 3.7 Sonnet (Reasoning)",
            "description": "The perfect balance of intelligence and speed. Excellent for most reasoning tasks.",
            "category": "balanced",
            "input_price": 3.00,
            "output_price": 15.00,
        },
        # ── Economy ──
        {
            "id": "claude-3-5-haiku-latest",
            "name": "Claude 3.5 Haiku (Fast)",
            "description": "Our fastest and most compact model, perfect for near-instant execution of simple tasks.",
            "category": "economy",
            "input_price": 0.80,
            "output_price": 4.00,
        },
    ],
    "ollama": [
        {
            "id": "mistral",
            "name": "Mistral 7B v0.3 (Ollama)",
            "description": "Powerful 7B parameter local model. Features a 32k context window, excellent logical reasoning, and native French support. Optimized for efficiency on consumer GPUs.",
            "category": "balanced",
            "input_price": 0.0,
            "output_price": 0.0,
        },
    ],
}

# ---------------------------------------------------------------------------
#  Embedding Models  (input_price only — embeddings have no "output" tokens)
# ---------------------------------------------------------------------------
EMBEDDING_MODELS: dict[str, ModelEntry] = {
    "models/gemini-embedding-001": {
        "id": "models/gemini-embedding-001",
        "name": "Gemini Embedding 001",
        "input_price": 0.15,
        "output_price": 0.0,
    },
    "text-embedding-3-small": {
        "id": "text-embedding-3-small",
        "name": "OpenAI Embedding 3 Small",
        "input_price": 0.020,
        "output_price": 0.0,
    },
    "text-embedding-3-large": {
        "id": "text-embedding-3-large",
        "name": "OpenAI Embedding 3 Large",
        "input_price": 0.130,
        "output_price": 0.0,
    },
    "text-embedding-ada-002": {
        "id": "text-embedding-ada-002",
        "name": "OpenAI Ada 002",
        "input_price": 0.100,
        "output_price": 0.0,
    },
    "mistral-embed": {
        "id": "mistral-embed",
        "name": "Mistral Embed",
        "input_price": 0.10,
        "output_price": 0.0,
    },
}

# ─── Grouped by Provider for UI Selectors ───

SUPPORTED_EMBEDDING_MODELS: dict[str, list[ModelEntry]] = {
    "gemini": [
        {
            "id": "gemini-embedding-001",
            "name": "Gemini Embedding 001",
            "description": "Stable, legacy-compatible embedding model. Great for consistent results across all Google Cloud regions.",
            "category": "economy",
            "input_price": 0.15,
            "output_price": 0.0,
        },
    ],
    "openai": [
        {
            "id": "text-embedding-3-small",
            "name": "OpenAI Embedding 3 Small",
            "description": "Highly efficient model from OpenAI. Great performance for general purpose search with 1536 dimensions.",
            "category": "balanced",
            "input_price": 0.020,
            "output_price": 0.0,
        },
        {
            "id": "text-embedding-3-large",
            "name": "OpenAI Embedding 3 Large",
            "description": "OpenAI's most capable model with up to 3072 dimensions. Best for complex semantic relationships and high accuracy.",
            "category": "flagship",
            "input_price": 0.130,
            "output_price": 0.0,
        },
    ],
    "ollama": [
        {
            "id": "bge-m3",
            "name": "BGE-M3 (Ollama)",
            "description": "Flagship multi-lingual model supporting 100+ languages. Features multi-granularity (sentences to docs) and 8192 context.",
            "category": "flagship",
            "input_price": 0.0,
            "output_price": 0.0,
        },
        {
            "id": "nomic-embed-text",
            "name": "Nomic Embed Text (Ollama)",
            "description": "High-performance open-source model. Features a massive 8192 context window and outperforms OpenAI Ada-002 on many benchmarks.",
            "category": "balanced",
            "input_price": 0.0,
            "output_price": 0.0,
        },
    ],
}

SUPPORTED_TRANSCRIPTION_MODELS: dict[str, list[ModelEntry]] = {
    "gemini": [
        {
            "id": "gemini-1.5-flash",
            "name": "Gemini 1.5 Flash",
            "description": "Fast and efficient for audio transcription.",
            "category": "balanced",
            "input_price": 0.075,
            "output_price": 0.30,
        },
        {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "description": "Highest quality transcription with 1M+ context.",
            "category": "flagship",
            "input_price": 1.25,
            "output_price": 10.00,
        },
    ],
    "openai": [
        {
            "id": "whisper-1",
            "name": "Whisper v2-large",
            "description": "State-of-the-art speech-to-text model from OpenAI.",
            "category": "flagship",
            "input_price": 0.006,  # Price is per minute, but we use token price placeholders for now
            "output_price": 0.0,
        },
    ],
    "ollama": [
        {
            "id": "whisper",
            "name": "Whisper (Ollama)",
            "description": "General-purpose speech recognition model.",
            "category": "balanced",
            "input_price": 0.0,
            "output_price": 0.0,
        },
    ],
}


# ---------------------------------------------------------------------------
#  Pricing Helpers  (used by PricingService)
# ---------------------------------------------------------------------------


def get_model_pricing(model_id: str) -> Optional[Tuple[float, float]]:
    """
    Look up (input_price, output_price) per 1M tokens for any model
    (chat or embedding).  Returns None if unknown.
    """
    # 1. Search chat models
    for models in SUPPORTED_CHAT_MODELS.values():
        for m in models:
            if m["id"] == model_id:
                return (m["input_price"], m["output_price"])

    # 2. Search embedding models
    if model_id in EMBEDDING_MODELS:
        e = EMBEDDING_MODELS[model_id]
        return (e["input_price"], e["output_price"])

    return None


def build_pricing_map() -> Dict[str, float]:
    """
    Build a flat model_id → blended_price_per_1k_tokens map.
    Used by the /api/v1/pricing endpoint for the frontend dashboard.

    Blended price = average of input and output prices,
    converted from per-1M to per-1K tokens.
    """
    prices: Dict[str, float] = {}

    # Chat models
    for models in SUPPORTED_CHAT_MODELS.values():
        for m in models:
            blended_per_1m = (m["input_price"] + m["output_price"]) / 2.0
            prices[m["id"]] = round(blended_per_1m / 1000.0, 8)  # per 1K tokens

    # Embedding models
    for model_id, m in EMBEDDING_MODELS.items():
        prices[model_id] = round(m["input_price"] / 1000.0, 8)  # per 1K tokens

    # Free providers
    prices["ollama"] = 0.0
    prices["local"] = 0.0

    # Fallback
    prices["default"] = 0.0001

    return prices


SUPPORTED_RERANK_MODELS: dict[str, list[ModelEntry]] = {
    "local": [
        {
            "id": "BAAI/bge-reranker-base",
            "name": "BGE Reranker Base (FastEmbed)",
            "description": "Balanced performance and efficiency. Good for general ranking tasks.",
            "category": "balanced",
            "input_price": 0.0,
            "output_price": 0.0,
        },
        {
            "id": "BAAI/bge-reranker-v2-m3",
            "name": "BGE Reranker v2 M3 (FastEmbed)",
            "description": "Latest generation M3 reranker. Superior accuracy and multilingual support.",
            "category": "flagship",
            "input_price": 0.0,
            "output_price": 0.0,
        },
    ],
    "cohere": [
        {
            "id": "rerank-v3.5",
            "name": "Cohere Rerank v3.5",
            "description": "Cohere's most advanced reranking model. Unmatched accuracy.",
            "category": "flagship",
            "input_price": 2.0,
            "output_price": 0.0,
        },
        {
            "id": "rerank-multilingual-v3.0",
            "name": "Cohere Rerank Multilingual v3.0",
            "description": "Optimized for high-accuracy reranking across 100+ languages.",
            "category": "balanced",
            "input_price": 1.0,
            "output_price": 0.0,
        },
        {
            "id": "rerank-english-v3.0",
            "name": "Cohere Rerank English v3.0",
            "description": "Fast and precise reranking for English-only content.",
            "category": "balanced",
            "input_price": 1.0,
            "output_price": 0.0,
        },
    ],
}

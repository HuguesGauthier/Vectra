import asyncio
import os
import sys
import httpx

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.core.settings import get_settings
from app.core.database import get_session_factory
from app.core.model_catalog import SUPPORTED_CHAT_MODELS, EMBEDDING_MODELS
from sqlalchemy import text


async def list_models():
    output_path = "mistral_models_output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        try:
            # 1. Get API Key from Database first
            api_key = None
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(text("SELECT value FROM settings WHERE key = 'mistral_api_key'"))
                api_key = result.scalar()

            # 2. If not in DB, check settings (ENV/.env)
            if not api_key:
                settings = get_settings()
                api_key = settings.MISTRAL_API_KEY

            if not api_key:
                f.write("❌ No Mistral API key found in database or environment.\n")
                return

            f.write(f"✅ Found API key.\n")

            # 3. Get Models from API
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.mistral.ai/v1/models", headers=headers)
                if response.status_code != 200:
                    f.write(f"❌ Error from Mistral API: {response.status_code} - {response.text}\n")
                    return

                api_models = response.json().get("data", [])
                api_ids = {m["id"] for m in api_models}

            # 4. Cross-reference with Catalog
            f.write(f"--- Available Mistral Models (Verified with Catalog) ---\n")
            f.write(f"{'Model ID':<30} | {'Name':<25} | {'Input ($/1M)':<15} | {'Output ($/1M)':<15}\n")
            f.write("-" * 95 + "\n")

            # Check Chat Models
            mistral_chat_models = SUPPORTED_CHAT_MODELS.get("mistral", [])
            for m in sorted(mistral_chat_models, key=lambda x: x["id"]):
                status = "✅" if m["id"] in api_ids else "❌ (Not in API list)"
                f.write(
                    f"{m['id']:<30} | {m['name']:<25} | {m['input_price']:<15} | {m['output_price']:<15} {status}\n"
                )

            # Check Embedding Models
            f.write("\n--- Embedding Models ---\n")
            for model_id, m in sorted(EMBEDDING_MODELS.items()):
                if "mistral" in m["name"].lower() or "mistral" in model_id:
                    status = "✅" if model_id in api_ids else "❌ (Not in API list)"
                    f.write(f"{model_id:<30} | {m['name']:<25} | {m['input_price']:<15} | {'N/A':<15} {status}\n")

            print(f"Done. Output in {output_path}")
        except Exception as e:
            f.write(f"❌ Error: {e}\n")
            import traceback

            f.write(traceback.format_exc())
            print(f"Failed. See {output_path}")


if __name__ == "__main__":
    asyncio.run(list_models())

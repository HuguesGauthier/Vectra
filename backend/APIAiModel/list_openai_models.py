import asyncio
import os
import sys
import httpx

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.core.database import get_session_factory
from app.core.model_catalog import SUPPORTED_CHAT_MODELS, EMBEDDING_MODELS
from sqlalchemy import text


async def list_models():
    output_path = "openai_models_output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        try:
            # 1. Get API Key
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(text("SELECT value FROM settings WHERE key = 'openai_api_key'"))
                api_key = result.scalar()

                if not api_key:
                    f.write("❌ No OpenAI API key found in database.\n")
                    return

                f.write(f"✅ Found API key.\n")

                # 2. Get Models from API
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

                async with httpx.AsyncClient() as client:
                    response = await client.get("https://api.openai.com/v1/models", headers=headers)
                    if response.status_code != 200:
                        f.write(f"❌ Error from OpenAI API: {response.status_code} - {response.text}\n")
                        return

                    api_models = response.json().get("data", [])
                    api_ids = {m["id"] for m in api_models}

            # 3. Cross-reference with Catalog
            f.write(f"--- Available OpenAI Models (Verified with Catalog) ---\n")
            f.write(f"{'Model ID':<30} | {'Name':<25} | {'Input ($/1M)':<15} | {'Output ($/1M)':<15}\n")
            f.write("-" * 90 + "\n")

            # Check Chat Models
            openai_chat_models = SUPPORTED_CHAT_MODELS.get("openai", [])
            for m in sorted(openai_chat_models, key=lambda x: x["id"]):
                status = "✅" if m["id"] in api_ids else "❌ (Not in API list)"
                f.write(
                    f"{m['id']:<30} | {m['name']:<25} | {m['input_price']:<15} | {m['output_price']:<15} {status}\n"
                )

            # Check Embedding Models
            f.write("\n--- Embedding Models ---\n")
            for model_id, m in sorted(EMBEDDING_MODELS.items()):
                # Only check OpenAI embeddings here for clarity, though gemini also in catalog
                if "openai" in m["name"].lower() or "ada" in model_id:
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

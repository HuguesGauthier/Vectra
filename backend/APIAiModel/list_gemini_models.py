import asyncio
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from google import genai
from app.core.database import get_session_factory
from sqlalchemy import text


async def list_models():
    output_path = "gemini_models_output.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                result = await session.execute(text("SELECT value FROM settings WHERE key = 'gemini_api_key'"))
                api_key = result.scalar()

                if not api_key:
                    f.write("❌ No Gemini API key found in database.\n")
                    return

                f.write(f"✅ Found API key.\n")
                client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

                f.write(f"--- Available Gemini Models ---\n")
                for model in client.models.list():
                    if "gemini" in model.name.lower():
                        f.write(f"- {model.name} ({model.display_name})\n")
            print(f"Done. Output in {output_path}")
        except Exception as e:
            f.write(f"❌ Error: {e}\n")
            import traceback

            f.write(traceback.format_exc())
            print(f"Failed. See {output_path}")


if __name__ == "__main__":
    asyncio.run(list_models())

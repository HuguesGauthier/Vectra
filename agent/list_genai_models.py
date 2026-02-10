import os
import sys

# Get the absolute path of the backend directory
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
sys.path.append(backend_path)

try:
    import google.generativeai as genai
    from app.core.settings import get_settings

    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        print("❌ Erreur: GEMINI_API_KEY n'est pas configuré.")
        sys.exit(1)

    genai.configure(api_key=settings.GEMINI_API_KEY)

    found = False
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            # We only want the model ID, and remove 'models/' prefix for readability
            print(m.name.replace("models/", ""))
            found = True

    if not found:
        print("⚠️ Aucun modèle trouvé.")

except Exception as e:
    print(f"❌ Erreur: {e}")

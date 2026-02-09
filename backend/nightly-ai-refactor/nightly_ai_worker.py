
import os
import glob
import sys
import subprocess
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
import shutil
import argparse

# Try importing git, if not present, use subprocess or warn
try:
    from git import Repo
    GIT_PYTHON_AVAILABLE = True
except ImportError:
    GIT_PYTHON_AVAILABLE = False
    print("⚠️ GitPython not found. Using subprocess for git operations where possible, but reliability may vary.")

# Charger les clés
# Explicitly look for .env in the backend directory if not found
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir) # Assuming script is in backend/nightly-ai-refactor
env_path = os.path.join(backend_dir, ".env")

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv() # Fallback to default search

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY not found in environment variables.")
    sys.exit(1)


# Configurer Gemini
genai.configure(api_key=GEMINI_API_KEY)

GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Using gemini-2.5-pro as requested (Best Latest)
model = genai.GenerativeModel(
    model_name="gemini-2.5-pro", 
    generation_config=GENERATION_CONFIG,
)

def run_linters(filepath):
    """Run black, isort, and flake8 on a file."""
    print(f"  🧹 Running Linters on {os.path.basename(filepath)}...")
    try:
        # Use sys.executable to ensure we use the venv's modules
        # Black and Isort (modify in place)
        subprocess.run([sys.executable, "-m", "black", filepath, "-q"], check=False)
        subprocess.run([sys.executable, "-m", "isort", filepath, "-q"], check=False)
        
        # Flake8 (capture output)
        result = subprocess.run([sys.executable, "-m", "flake8", filepath], capture_output=True, text=True, check=False)
        return result.stdout
    except Exception as e:
        print(f"  ⚠️ Error running linters: {e}")
        return ""

# --- CONFIGURATION ---
# Adjust paths based on execution location
# If running creating backend/nightly-ai-refactor/nightly_ai_worker.py
# PROJECT_PATH should be backend/app to scan source code
PROJECT_PATH = os.path.join(backend_dir, "app") 
TESTS_PATH = os.path.join(backend_dir, "tests")
os.makedirs(TESTS_PATH, exist_ok=True)

def get_git_ready():
    """Crée une branche de sécurité pour la nuit"""
    branch_name = f"nightly-ai-{datetime.now().strftime('%Y-%m-%d')}"
    
    if GIT_PYTHON_AVAILABLE:
        repo = Repo(backend_dir if os.path.isdir(os.path.join(backend_dir, ".git")) else os.path.dirname(backend_dir))
        # This assumes the repo root is at backend/.. or backend/.
        # Let's try to find repo root
        try:
             # Find git root
            repo_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=backend_dir).decode('utf-8').strip()
            repo = Repo(repo_root)
        except Exception:
             repo = Repo(".") # Fallback

        # Check if we are already on the target branch
        try:
            if repo.active_branch.name == branch_name:
                print(f"🌿 Already on branch: {branch_name}")
                return repo, branch_name
        except:
            pass

        # S'assurer qu'on est à jour (seulement si on change de branche)
        try:
            repo.git.checkout('main')
            repo.git.pull()
        except Exception as e:
             print(f"⚠️ Could not checkout main/pull: {e}. Proceeding from current state.")

        # Check if branch exists
        try:
            repo.git.checkout(branch_name)
            print(f"🌿 Checked out existing branch: {branch_name}")
        except:
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            print(f"🌿 Created and checked out branch: {branch_name}")
            
        return repo, branch_name
    else:
        # Fallback to subprocess
        print("Using subprocess for Git...")
        cmd_checkout_main = ["git", "checkout", "main"]
        cmd_pull = ["git", "pull"]
        cmd_checkout_branch = ["git", "checkout", "-b", branch_name]
        
        subprocess.run(cmd_checkout_main, cwd=backend_dir, check=False)
        subprocess.run(cmd_pull, cwd=backend_dir, check=False)
        if subprocess.run(cmd_checkout_branch, cwd=backend_dir, check=False).returncode != 0:
             # Branch might exist
             subprocess.run(["git", "checkout", branch_name], cwd=backend_dir, check=False)
        
        return None, branch_name


def get_architect_prompt():
    """Read the prompt_architect_P0.md file."""
    try:
        # Assuming doc is at backend/../doc/prompt_architect_P0.md
        # backend_dir is already defined globally
        prompt_path = os.path.join(os.path.dirname(backend_dir), "doc", "prompt_architect_P0.md")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            print(f"  ⚠️ Prompt file not found at {prompt_path}, using default.")
            return None
    except Exception as e:
        print(f"  ⚠️ Error reading prompt file: {e}")
        return None

def ai_refactor(file_content, filename, lint_output, architect_prompt_template):
    """Refactor using the Architect Prompt."""
    
    if architect_prompt_template:
        prompt = f"""
        {architect_prompt_template}
        
        ---
        
        **CONTEXTE TECHNIQUE SUPPLÉMENTAIRE :**
        Voici le rapport Flake8 actuel sur ce fichier (corrige ces erreurs si pertinent) :
        {lint_output}
        
        **INSTRUCTION DE SORTIE CRITIQUE :**
        Je veux que tu me renvoies UNIQUEMENT le code Python refactoré final dans un bloc de code.
        Ne renvoie PAS le rapport d'audit, ni le tableau, ni les tests, ni le commit message demandés dans le prompt original pour cette étape spécifique.
        Je veux JUSTE le code pour remplacer le fichier existant.
        
        FICHIER À REFACTORER ({filename}) :
        {file_content}
        """
    else:
        # Fallback to previous prompt if file not found
        prompt = f"""
        Tu es un Expert Senior Python (Google Style).
        Voici le fichier '{filename}'.
        
        TES TÂCHES :
        1. Ajoute des Type Hints (typing) partout où ils manquent.
        2. Ajoute des Docstrings (format Google) aux fonctions/classes.
        3. Optimise le code si tu vois des boucles inefficaces ou du code redondant.
        4. Garde la logique EXACTEMENT la même. Ne brise rien.
        
        IMPORTANT : Renvoie SEULEMENT le code Python complet, sans markdown (```), sans blabla.
        
        CODE :
        {file_content}
        """
        
    try:
        response = model.generate_content(prompt)
        # Clean markdown
        text = response.text
        if "```python" in text:
            parts = text.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0]
                return code_part.strip()
        elif "```" in text:
             parts = text.split("```")
             if len(parts) > 1:
                code_part = parts[1]
                return code_part.strip()
        
        return text.strip()
    except Exception as e:
        print(f"Gemini Error: {e}")
        raise


def find_existing_test(filename, tests_path):
    """Try to find a corresponding test file in tests/"""
    # Simple heuristic: test_{filename} or {filename}_test.py
    # or inside subfolders.
    
    # Cleaning filename
    base_name = filename.replace(".py", "")
    
    # Search for test_{base_name}.py recursively
    candidates = glob.glob(f"{tests_path}/**/test_{base_name}.py", recursive=True)
    if candidates:
        return candidates[0]
        
    return None

def ai_create_tests(refactored_code, filename, existing_test_content=None):
    """Generate or Update pytest tests."""
    
    if existing_test_content:
        prompt = f"""
        Tu es un expert Pytest.
        
        CONTEXTE :
        Nous venons de refactoriser le fichier '{filename}'.
        Il existe déjà des tests pour ce fichier.
        
        CODE REFACTORISÉ :
        {refactored_code}
        
        TESTS EXISTANTS :
        {existing_test_content}
        
        TACHE :
        Mets à jour les tests existants pour qu'ils matchent le nouveau code (type hints, structure).
        - Garde la couverture de test existante.
        - Ajoute des tests si de nouvelles fonctions ont été révélées ou si la couverture semble faible.
        - Utilise `pytest` et `unittest.mock` si besoin.
        
        DOIT RETOURNER :
        UNIQUEMENT le code Python des tests mis à jour.
        """
    else:
        prompt = f"""
        Tu es un expert Pytest.
        
        CONTEXTE :
        Nous venons de refactoriser le fichier '{filename}'.
        Il n'y a PAS encore de tests pour ce fichier.
        
        CODE REFACTORISÉ :
        {refactored_code}
        
        TACHE :
        Crée une suite de tests complète pour ce fichier.
        - Couvre les cas nominaux et les cas d'erreur.
        - Utilise `pytest`.
        - Mock les dépendances externes ou la base de données.
        
        DOIT RETOURNER :
        UNIQUEMENT le code Python des tests.
        """

    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```python" in text:
            parts = text.split("```python")
            if len(parts) > 1:
                code_part = parts[1].split("```")[0]
                return code_part.strip()
        elif "```" in text:
             parts = text.split("```")
             if len(parts) > 1:
                code_part = parts[1]
                return code_part.strip()
        
        return text.strip()
    except Exception as e:
        print(f"Gemini Error (Tests): {e}")
        return ""

def main():
    print("🚀 Démarrage du Nightly AI Worker...")
    
    parser = argparse.ArgumentParser(description="Nightly AI Refactor Worker")
    parser.add_argument("file", nargs="?", help="Specific file to refactor (optional)")
    args = parser.parse_args()

    # 0. Load Architect Prompt
    architect_prompt = get_architect_prompt()
    if architect_prompt:
        print("📜 Expert Architect Prompt loaded.")
    else:
        print("⚠️ Using default refactor prompt.")

    # 1. Sécurité Git
    repo, branch_name = get_git_ready()
    
    # 2. Lister les fichiers Python (on exclut les tests existants et venv)
    if args.file:
        raw_path = args.file
        # Try to resolve path intelligently
        # 1. Absolute path or relative to CWD
        candidate_1 = os.path.abspath(raw_path)
        # 2. If 'backend/' is in start, but we are already in backend, try stripping it
        # (User might tab-complete from root)
        candidate_2 = os.path.abspath(raw_path.replace("backend\\", "").replace("backend/", "")) if "backend" in raw_path else None
        
        target_file = None
        if os.path.exists(candidate_1) and os.path.isfile(candidate_1):
            target_file = candidate_1
        elif candidate_2 and os.path.exists(candidate_2) and os.path.isfile(candidate_2):
            target_file = candidate_2
            
        if not target_file:
            print(f"❌ File not found: {raw_path}")
            print(f"   Checked: {candidate_1}")
            if candidate_2: print(f"   Checked: {candidate_2}")
            sys.exit(1)
        
        # Verify it's a python file and not in excluded dirs (optional, but good safety)
        if not target_file.endswith(".py"):
             print("⚠️ Warning: Target file does not end with .py")
             
        files = [target_file]
        print(f"🎯 Targeting single file: {target_file}")
    else:
        print(f"Scanning {PROJECT_PATH}...")
        files = glob.glob(f"{PROJECT_PATH}/**/*.py", recursive=True)
        files = [f for f in files if "venv" not in f and "tests" not in f and "__init__" not in f and "migrations" not in f]
    
    print(f"Found {len(files)} files to process.")

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"Processing {filename}...")
        
        # --- ÉTAPE 0 : LINTING ---
        lint_output = run_linters(filepath)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                original_code = f.read()
        except UnicodeDecodeError:
            print(f"  ❌ Skipping binary or non-utf8 file: {filename}")
            continue
            
        # --- ÉTAPE A : REFACTORING ---
        try:
            new_code = ai_refactor(original_code, filename, lint_output, architect_prompt)
            if not new_code.strip():
                 print("  ⚠️ Empty response from AI, skipping save.")
                 continue

            # On écrase le fichier avec la version améliorée (safe car on est sur une branche)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_code)
            print(f"  ✅ Refactored")
        except Exception as e:
            print(f"  ❌ Erreur Refactor sur {filename}: {e}")
            continue

        # --- ÉTAPE B : GESTION DES TESTS ---
        try:
            # Check for existing tests
            existing_test_path = find_existing_test(filename, TESTS_PATH)
            existing_content = None
            
            if existing_test_path:
                print(f"  Item 'Test' exists at: {existing_test_path}")
                try:
                    with open(existing_test_path, "r", encoding="utf-8") as f:
                        existing_content = f.read()
                except Exception:
                    print("  ⚠️ Could not read existing test, generating new ones.")
            
            # Re-read the NEW code to generate tests against what we just wrote
            with open(filepath, "r", encoding="utf-8") as f:
                refactored_content = f.read()

            test_code = ai_create_tests(refactored_content, filename, existing_content) 
            
            if not test_code.strip():
                 print("  ⚠️ Empty test response from AI.")
                 continue
            
            # Determine where to save
            if existing_test_path:
                save_path = existing_test_path
                action_msg = "Updated existing tests"
            else:
                test_filename = f"test_{filename}"
                save_path = os.path.join(TESTS_PATH, test_filename)
                action_msg = "Generated new tests"

            with open(save_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            print(f"  ✅ {action_msg}")

        except Exception as e:
             print(f"  ❌ Erreur Tests sur {filename}: {e}")

    # 3. Lancer Black/Isort pour nettoyer le code de l'IA (Final pass)
    print("🧹 Passage de Black et Isort (Final)...")
    
    # Define target for final cleanup
    cleanup_target = "."
    if args.file:
         # If single file, only run on that file (and its test)
         # We can't easily guess the test file here without logic duplication, 
         # but running on the specific file is better than nothing.
         # Actually, we should probably run on the file AND the tests dir if simple, 
         # but let's stick to "." if simple, OR just the file if careful.
         # User complained about "parsing all files", which was Black reformatting everything.
         cleanup_target = target_file if target_file else "."

    try:
        subprocess.run([sys.executable, "-m", "black", cleanup_target], cwd=backend_dir, check=False)
        subprocess.run([sys.executable, "-m", "isort", cleanup_target], cwd=backend_dir, check=False)
    except Exception as e:
        print(f"⚠️ Error running final formatting: {e}")

    # 4. Git Commit
    if GIT_PYTHON_AVAILABLE and repo:
        try:
            repo.git.add(A=True)
            repo.index.commit(f"Nightly AI Refactor & Tests - {datetime.now()}")
            print(f"🏁 Terminé ! Branche '{branch_name}' prête pour review.")
        except Exception as e:
             print(f"Error commiting: {e}")
    else:
        subprocess.run(["git", "add", "."], cwd=backend_dir)
        subprocess.run(["git", "commit", "-m", f"Nightly AI Refactor & Tests - {datetime.now()}"], cwd=backend_dir)
        print(f"🏁 Terminé ! Branche '{branch_name}' prête pour review.")

if __name__ == "__main__":
    main()

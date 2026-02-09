Agis en tant que **Senior Principal Python Backend Architect & Security Auditor** (Expert FastAPI, SQLAlchemy, AsyncIO, Qdrant/Vector DB).

**MISSION :**
Effectue une "Deep Code Review" impitoyable du fichier fourni.
Ne laisse rien passer. Ton objectif est de blinder le code pour la production (Sécurité, Scalabilité, Maintenabilité).

**CRITÈRES D'ANALYSE ÉTENDUS (Checklist V2) :**

1.  **🔴 P0 - CRITIQUE (Sécurité & Stabilité Immédiate) :**
    - **Secrets & Config :** Clés API, mots de passe, sels en dur.
    - **Injections & Sanitization :** SQLi, Command Injection, XSS (si retour HTML), Logs affichant des PII/Secrets.
    - **Async Blocking (Event Loop Killer) :** Appels synchrones (`requests`, `time.sleep`, IO fichier lourd, CPU intensif) dans `async def`.
    - **Auth & Permissions :** Routes publiques non voulues, absence de `Depends(get_current_user)`, `Scopes` manquants.
    - **DoS & Limites :** Uploads de fichiers sans limite de taille (`Read` infini), Pagination absente (retourne 1M de lignes), pas de Rate Limiting.
    - **Data Leaks :** Renvoi d'objets ORM bruts sans modèle Pydantic `response_model` (risque d'exposer hash pwd / ids internes).

2.  **🟠 P1 - ARCHITECTURE & PERFORMANCE (Scalabilité) :**
    - **Couplage & DI :** Instanciation directe (`Service()`) au lieu de l'Injection (`Depends()`).
    - **N+1 Queries :** Boucles effectuant des appels SQL ou API externes à chaque itération.
    - **DB/Vector Lifecycle :** Session non scopée, connexion Qdrant réouverte à chaque requête (au lieu de Singleton/Pool).
    - **Transactions (ACID) :** Manque de `commit/rollback` ou opérations SQL + Vector non atomiques (risque de désynchronisation).
    - **Circuit Breakers :** Appels API externes (Gemini/OpenAI) sans `timeout` ni gestion de retry (le serveur pend indéfiniment).
    - **Single Responsibility Principle :** Si tu n'arrives pas à nommer ta fonction avec un verbe précis, c'est souvent parce que ta fonction fait trop de choses en même temps. C'est un signe qu'il faut la découper (Single Responsibility Principle).

3.  **🟡 P2 - STANDARDS & ROBUSTESSE :**
    - **Error Handling :** `except Exception:` silencieux ou générique. Pas de logging structuré (print vs logger).
    - **Configuration :** `os.getenv` éparpillé (pas de `pydantic-settings`).
    - **Typage Strict :** Utilisation de `Any`, `dict` sans schéma, absence de validation Pydantic V2.
    - **RAG Specifics :** Vérification des dimensions des vecteurs manquant, manque de normalisation des inputs textes.

4.  **🔵 P3 - CLEAN CODE & MAINTENABILITÉ :**
    - **DRY :** Logique dupliquée.
    - **Testabilité :** Utilisation de `datetime.now()` ou `uuid.uuid4()` au milieu du code (difficile à mocker).
    - **Magic Literals :** Chaînes/Nombres magiques.
    - **Clarté :** Nommage ambigu, fonctions > 50 lignes.
    - **Naming Convention :** Dans la couche Service, vérifie les noms CRUD (create, update, delete) par des verbes d'intention métier (register, onboard, archive, process) qui décrivent la finalité de l'action. Utilisez get* pour les retours obligatoires (raise 404) et find* pour les optionnels.

**FORMAT DE SORTIE ATTENDU :**

1.  **📊 Audit Score (/100) :** Note honnête et sévère.

2.  **📋 Tableau des Priorités (Trié par Sévérité) :**
    | Priorité | Ligne | Problème | Risque | Correction |
    | :--- | :--- | :--- | :--- | :--- |
    | 🔴 P0 | L.12 | Async Blocking | DoS | Utiliser `aiofiles` ou `run_in_executor` |

3.  **🛠️ Refactoring "Architecte" :**
    Réécris le code complet (ou les segments clés) en appliquant **tous** les correctifs.
    - Utilise `Annotated` pour les dépendances (Best Practice FastAPI moderne).
    - Sépare la logique DB dans un Repository si nécessaire.

4.  **✅ Tests Unitaires (Pytest) :**
    Fournis 2 cas de tests (Success + Failure) utilisant `AsyncMock` pour valider la correction.

5.  **📝 Git Commit Message (Conventional Commits) :**
    Rédige le message de commit prêt à l'emploi pour valider ce refactoring.
    - **Format :** `type(scope): description`
    - **Body :** Liste à puces détaillée des changements techniques ("Why & What").

**MON FICHIER À ANALYSER :**

# Centralized Prompt Store for Vectra
# Patterns: Jinja2-style placeholders allowed.

REWRITE_QUESTION_PROMPT = (
    "Given the following conversation history and a follow-up question, "
    "rephrase the follow-up question to be a standalone question.\n"
    "Chat History:\n{chat_history}\n"
    "Follow Up Input: {question}\n"
    "Standalone Question:"
)

RAG_ANSWER_PROMPT = (
    "{role_instruction}\n\n"
    "### CHAT HISTORY ###\n"
    "{chat_history}\n"
    "### END CHAT HISTORY ###\n\n"
    "### CONTEXT ###\n"
    "{context_str}\n"
    "### END CONTEXT ###\n\n"
    "Global Instructions:\n"
    "1. Use the Context and Chat History to answer the question.\n"
    "2. Prioritize the Context for factual information about documents.\n"
    "3. Use Chat History for continuity (remembering names, previous topics).\n"
    "4. If the answer is not in the context or history, you may use your general knowledge ONLY for small talk (greetings, compliments). For specific domain questions, state that you do not know.\n"
    "5. **CRITICAL:** Detect the language of the User Question below. Your Answer MUST be in that EXACT same language.\n"
    "6. If the Context is in French but the Question is in English, you MUST TRANSLATE the information into English.\n"
    "7. **Presenting Data:** If the answer involves a list or comparison that fits a table, YOU MUST Output it using the special `:::table` block format below. Do not use Markdown tables.\n"
    "   Format:\n"
    "   :::table\n"
    "   {\n"
    '     "columns": [{"name": "col_key", "label": "Column Label", "field": "col_key", "sortable": true, "align": "left"}],\n'
    '     "data": [{"col_key": "Value"}]\n'
    "   }\n"
    "   :::\n"
    "Question: {query_str}"
)

AGENTIC_RESPONSE_PROMPT = (
    "You are a helpful assistant. Use the following pieces of context to answer the user's question.\n"
    "If the answer is not in the context, say so.\n"
    "\n"
    "### CONTEXT ###\n"
    "{context_str}\n"
    "### END CONTEXT ###\n"
    "\n"
    "Global Instructions:\n"
    "1. Answer in the same language as the user's question (French or English).\n"
    "2. **Charts:** If the user asks for a chart (pie, bar, etc.), reply affirmatively (e.g., 'Here is the chart based on the data...'). NEVER say you cannot generate charts, as the UI will render it for you.\n"
    "3. **Presenting Data:** If the answer involves a list or comparison that fits a table, YOU MUST Output it using the special `:::table` block format below. Do not use Markdown tables.\n"
    "   Format:\n"
    "   :::table\n"
    "   {\n"
    '     "columns": [{"name": "col_key", "label": "Column Label", "field": "col_key", "sortable": true, "align": "left"}],\n'
    '     "data": [{"col_key": "Value"}]\n'
    "   }\n"
    "   :::\n"
    "\n"
    "Question: {query_str}\n"
    "Answer:"
)

AGENTIC_RESPONSE_PROMPT_FR = (
    "Vous êtes un assistant utile. Utilisez les éléments de contexte suivants pour répondre à la question de l'utilisateur.\n"
    "Si la réponse n'est pas dans le contexte, dites-le.\n"
    "\n"
    "### CONTEXTE ###\n"
    "{context_str}\n"
    "### FIN CONTEXTE ###\n"
    "\n"
    "Instructions Globales:\n"
    "1. Répondez strictement en Français.\n"
    "2. **Graphiques:** Si l'utilisateur demande un graphique, répondez positivement (ex: 'Voici le graphique demandé basé sur les données...'). Ne dites JAMAIS que vous ne pouvez pas générer d'images. L'interface va générer le graphique.\n"
    "3. **Présentation des données:** Si la réponse implique une liste ou une comparaison qui s'adapte à un tableau, VOUS DEVEZ la sortir en utilisant le format de bloc spécial `:::table` ci-dessous. N'utilisez pas de tableaux Markdown.\n"
    "   Format:\n"
    "   :::table\n"
    "   {\n"
    '     "columns": [{"name": "col_key", "label": "Libellé Colonne", "field": "col_key", "sortable": true, "align": "left"}],\n'
    '     "data": [{"col_key": "Valeur"}]\n'
    "   }\n"
    "   :::\n"
    "\n"
    "Question: {query_str}\n"
    "Réponse:"
)

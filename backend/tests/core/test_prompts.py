import pytest
from app.core import prompts


class TestPromptsCore:
    def test_prompts_loaded(self):
        """Happy Path: Verify all key prompts are loaded and non-empty."""
        assert prompts.REWRITE_QUESTION_PROMPT
        assert prompts.RAG_ANSWER_PROMPT
        assert prompts.AGENTIC_RESPONSE_PROMPT
        assert prompts.AGENTIC_RESPONSE_PROMPT_FR

    def test_prompts_template_structure(self):
        """Happy Path: Verify prompts contain expected Pydantic/LlamaIndex placeholders."""
        assert "{chat_history}" in prompts.REWRITE_QUESTION_PROMPT
        assert "{question}" in prompts.REWRITE_QUESTION_PROMPT

        assert "{context_str}" in prompts.RAG_ANSWER_PROMPT
        assert "{query_str}" in prompts.RAG_ANSWER_PROMPT

        assert "{context_str}" in prompts.AGENTIC_RESPONSE_PROMPT
        assert "{query_str}" in prompts.AGENTIC_RESPONSE_PROMPT

    def test_no_duplicate_closures(self):
        """Worst Case: Ensure the bug (duplicate ::: closures) is fixed and doesn't regress."""
        bad_pattern = ":::\n   :::"
        assert bad_pattern not in prompts.RAG_ANSWER_PROMPT
        assert bad_pattern not in prompts.AGENTIC_RESPONSE_PROMPT
        assert bad_pattern not in prompts.AGENTIC_RESPONSE_PROMPT_FR

        # Also check for exact string literal repeat if whitespace differs
        assert ":::\n   :::\n" not in prompts.RAG_ANSWER_PROMPT
        assert ":::\n   :::\n" not in prompts.AGENTIC_RESPONSE_PROMPT
        assert ":::\n   :::\n" not in prompts.AGENTIC_RESPONSE_PROMPT_FR

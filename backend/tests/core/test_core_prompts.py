import pytest

from app.core.prompts import RAG_ANSWER_PROMPT, REWRITE_QUESTION_PROMPT


class TestPrompts:
    def test_rewrite_question_prompt_placeholders(self):
        """Verify the rewrite prompt contains required keys."""
        assert "{chat_history}" in REWRITE_QUESTION_PROMPT
        assert "{question}" in REWRITE_QUESTION_PROMPT

    def test_rag_answer_prompt_placeholders(self):
        """Verify the RAG answer prompt contains required keys."""
        assert "{role_instruction}" in RAG_ANSWER_PROMPT
        assert "{context_str}" in RAG_ANSWER_PROMPT
        assert "{query_str}" in RAG_ANSWER_PROMPT

    def test_prompts_are_not_empty(self):
        """Sanity check that prompts are not empty strings."""
        assert len(REWRITE_QUESTION_PROMPT) > 50
        assert len(RAG_ANSWER_PROMPT) > 50

import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import asyncio

from app.factories.rerank_factory import RerankProviderFactory

class TestRerankProviderFactory:
    @pytest.mark.asyncio
    async def test_create_cohere_reranker(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "fake-cohere-key"

        # Mock cohere module
        mock_cohere = MagicMock()
        mock_cohere.AsyncClient = MagicMock()
        
        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            client = await RerankProviderFactory.create_reranker("cohere", mock_settings)
            
            assert client is not None
            mock_cohere.AsyncClient.assert_called_once_with(api_key="fake-cohere-key")

    @pytest.mark.asyncio
    async def test_create_local_reranker(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "BAAI/bge-reranker-base"

        # Mock fastembed module
        mock_fastembed = MagicMock()
        mock_fastembed.TextReranker = MagicMock()
        
        with patch.dict(sys.modules, {"fastembed": mock_fastembed}):
            # Reset singleton for test
            RerankProviderFactory._local_reranker = None
            
            reranker = await RerankProviderFactory.create_reranker("local", mock_settings)
            
            assert reranker is not None
            mock_fastembed.TextReranker.assert_called_once_with(model_name="BAAI/bge-reranker-base")

    @pytest.mark.asyncio
    async def test_unknown_provider_defaults_to_local(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "BAAI/bge-reranker-base"

        # Mock fastembed module
        mock_fastembed = MagicMock()
        mock_fastembed.TextReranker = MagicMock()
        
        with patch.dict(sys.modules, {"fastembed": mock_fastembed}):
            # Reset singleton for test
            RerankProviderFactory._local_reranker = None
            
            reranker = await RerankProviderFactory.create_reranker("unknown", mock_settings)
            
            assert reranker is not None
            mock_fastembed.TextReranker.assert_called_once()

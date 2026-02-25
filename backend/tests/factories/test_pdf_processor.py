"""
Tests for PDF processor with smart local-first routing.

Updated to test the new quality-based routing strategy with Gemini.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.factories.processors.base import ProcessedDocument
from app.factories.processors.pdf_processor import PdfProcessor


@pytest.fixture
def mock_settings():
    with patch("app.factories.processors.pdf_processor.get_settings") as mock:
        mock.return_value.GEMINI_API_KEY = "test-key"
        yield mock


class TestPdfProcessorBasics:
    """Basic functionality tests."""

    @pytest.mark.asyncio
    async def test_get_supported_extensions(self, mock_settings):
        """Should only support pdf extension."""
        processor = PdfProcessor()
        extensions = processor.get_supported_extensions()
        assert extensions == ["pdf"]

    @pytest.mark.asyncio
    async def test_initialization_with_api_key(self, mock_settings):
        """Processor should initialize correctly with API key."""
        processor = PdfProcessor()
        assert processor is not None
        assert processor._has_api_key is True

    @pytest.mark.asyncio
    async def test_initialization_without_api_key(self):
        """Processor should initialize correctly without API key."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.GEMINI_API_KEY = None
            mock_get_settings.return_value = mock_settings
            processor = PdfProcessor()
            assert processor._has_api_key is False


class TestPdfProcessorLocalFirstRouting:
    """Tests for local-first routing strategy."""

    @pytest.mark.asyncio
    async def test_local_success_high_quality_stays_local(self):
        """High quality local result should be kept (no cloud call)."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            # Mock local processor returning good quality text
            good_text = "This is a well-formatted PDF document with sufficient content for quality analysis."
            local_result = [ProcessedDocument(content=good_text, metadata={"page_count": 1}, success=True)]

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = local_result
                mock_inspector.calculate_quality_score.return_value = 100
                mock_inspector.should_use_cloud.return_value = False

                result = await processor.process("test.pdf")

                # Verify local was called
                mock_local.assert_called_once()

                # Verify cloud was NOT called (cost optimization)
                mock_cloud.assert_not_called()

                # Verify result is the local one
                assert result[0].content == good_text
                assert result[0].success is True

    @pytest.mark.asyncio
    async def test_local_poor_quality_routes_to_cloud(self):
        """Poor quality local result should trigger cloud fallback."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            # Mock local processor returning poor quality text
            poor_text = "1"  # Just a page number
            local_result = [ProcessedDocument(content=poor_text, metadata={"page_count": 1}, success=True)]

            # Mock cloud processor returning better result
            cloud_json = '[{"page_number": 1, "content": "This is the Gemini extraction result with full content."}]'
            cloud_result = [
                ProcessedDocument(
                    content="This is the Gemini extraction result with full content.",
                    metadata={"source_tool": "Gemini", "page_number": 1},
                    success=True,
                )
            ]

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = local_result
                mock_cloud.return_value = (
                    cloud_result  # The processor returns this, the mock inside CloudProcessor returns JSON
                )
                mock_inspector.calculate_quality_score.return_value = 10  # Low score
                mock_inspector.should_use_cloud.return_value = True

                result = await processor.process("test.pdf")

                # Verify both were called
                mock_local.assert_called_once()
                mock_cloud.assert_called_once()

                # Verify result is the cloud one
                assert result[0].content == "This is the Gemini extraction result with full content."
                assert result[0].metadata["source_tool"] == "Gemini"

    @pytest.mark.asyncio
    async def test_local_empty_text_routes_to_cloud_ocr(self):
        """Empty text (scanned PDF) should route to cloud for OCR."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            # Mock local processor returning empty (scanned PDF)
            local_result = [ProcessedDocument(content="", metadata={"page_count": 1}, success=True)]  # Empty = scanned

            # Mock cloud processor with OCR result
            cloud_result = [
                ProcessedDocument(
                    content="OCR extracted text from scanned image",
                    metadata={"source_tool": "Gemini", "page_number": 1},
                    success=True,
                )
            ]

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = local_result
                mock_cloud.return_value = cloud_result
                mock_inspector.calculate_quality_score.return_value = 0
                mock_inspector.should_use_cloud.return_value = True

                result = await processor.process("test.pdf")

                mock_local.assert_called_once()
                mock_cloud.assert_called_once()
                assert result[0].content == "OCR extracted text from scanned image"


class TestPdfProcessorNoCloudKey:
    """Tests for scenarios without cloud API key."""

    @pytest.mark.asyncio
    async def test_no_api_key_keeps_local_result(self):
        """Without API key, should keep local result even if poor quality."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = None
            processor = PdfProcessor()
            assert processor._has_api_key is False

            # Mock local processor with poor quality
            poor_text = "Page 1"
            local_result = [ProcessedDocument(content=poor_text, metadata={}, success=True)]

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = local_result
                mock_inspector.calculate_quality_score.return_value = 10
                mock_inspector.should_use_cloud.return_value = True

                result = await processor.process("test.pdf")

                # Verify local was called
                mock_local.assert_called_once()

                # Verify cloud was NOT called (no API key)
                mock_cloud.assert_not_called()

                # Verify we kept the poor local result (no alternative)
                assert result[0].content == poor_text

    @pytest.mark.asyncio
    async def test_no_api_key_local_failure_returns_error(self):
        """Without API key, local failure should return error."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = None
            processor = PdfProcessor()

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = [
                    ProcessedDocument(content="", metadata={}, success=False, error_message="pypdf failed")
                ]

                result = await processor.process("test.pdf")

                # Should return the error from local
                assert result[0].success is False


class TestPdfProcessorErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_validation_error_returns_error_document(self, mock_settings):
        """File validation error should return error document."""
        processor = PdfProcessor()

        result = await processor.process("/nonexistent/file.pdf")

        assert result[0].success is False
        assert "File not found" in result[0].error_message

    @pytest.mark.asyncio
    async def test_local_exception_tries_cloud(self):
        """Exception in local processor should trigger cloud fallback."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            cloud_result = [ProcessedDocument(content="Cloud content", metadata={}, success=True)]

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.side_effect = Exception("Unexpected local error")
                mock_cloud.return_value = cloud_result

                result = await processor.process("test.pdf")

                # Should have tried cloud after local exception
                mock_cloud.assert_called_once()
                assert result[0].success is True

    @pytest.mark.asyncio
    async def test_cloud_exception_returns_error(self):
        """Exception in cloud processor should return error document."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.return_value = [ProcessedDocument(content="", metadata={}, success=True)]
                mock_inspector.should_use_cloud.return_value = True
                mock_cloud.side_effect = Exception("Cloud API error")

                result = await processor.process("test.pdf")

                assert result[0].success is False
                assert "Unexpected cloud error" in result[0].error_message


class TestPdfProcessorCostOptimization:
    """Tests to verify cost optimization behavior."""

    @pytest.mark.asyncio
    async def test_cost_optimization_local_accepted(self):
        """Verify that good local results save cloud costs."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            # 10 PDFs with good quality text
            good_pdfs = []
            for i in range(10):
                good_text = f"Document {i} with sufficient content for quality analysis."
                good_pdfs.append([ProcessedDocument(content=good_text, metadata={}, success=True)])

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.side_effect = good_pdfs
                mock_inspector.should_use_cloud.return_value = False

                # Process 10 PDFs
                for i in range(10):
                    await processor.process("test.pdf")

                # Verify local called 10 times
                assert mock_local.call_count == 10

                # Verify cloud called 0 times (100% cost savings)
                assert mock_cloud.call_count == 0

    @pytest.mark.asyncio
    async def test_cost_optimization_mixed_quality(self):
        """Verify mixed quality PDFs only use cloud when necessary."""
        with patch("app.factories.processors.pdf_processor.get_settings") as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "valid-key"
            processor = PdfProcessor()

            # 8 good quality, 2 poor quality
            results = []
            qualities = []

            for i in range(8):
                results.append([ProcessedDocument(content="Good content", metadata={}, success=True)])
                qualities.append(False)  # should_use_cloud = False

            for i in range(2):
                results.append([ProcessedDocument(content="", metadata={}, success=True)])
                qualities.append(True)  # should_use_cloud = True

            with (
                patch.object(processor._local_processor, "process", new_callable=AsyncMock) as mock_local,
                patch.object(processor._cloud_processor, "process", new_callable=AsyncMock) as mock_cloud,
                patch.object(processor, "_validate_file_path", new_callable=AsyncMock) as mock_validate,
                patch("app.factories.processors.pdf_processor.PdfQualityInspector") as mock_inspector,
            ):

                mock_validate.return_value = "test.pdf"
                mock_local.side_effect = results
                mock_cloud.return_value = [ProcessedDocument(content="Cloud OCR", metadata={}, success=True)]
                mock_inspector.should_use_cloud.side_effect = qualities

                # Process 10 PDFs
                for i in range(10):
                    await processor.process("test.pdf")

                # Verify local called 10 times (always tried first)
                assert mock_local.call_count == 10

                # Verify cloud called only 2 times (20% of PDFs)
                assert mock_cloud.call_count == 2

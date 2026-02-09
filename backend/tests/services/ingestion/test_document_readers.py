import asyncio
import os
from unittest.mock import ANY, AsyncMock, MagicMock, mock_open, patch
from uuid import uuid4

import pandas as pd
import pytest

from app.core.exceptions import (FileSystemError, FunctionalError,
                                 TechnicalError)
from app.services.ingestion.document_readers import (AudioReader, CSVReader,
                                                     ReaderFactory,
                                                     StandardReader,
                                                     TextStreamReader)


class TestCSVReader:
    def test_read_success(self):
        reader = CSVReader()
        file_path = "test.csv"

        mock_df = pd.DataFrame({"id": [1], "content": ["foo"]})

        with patch("pandas.read_csv") as mock_read:
            # Mock context manager for chunksize
            mock_read.return_value.__enter__.return_value = [mock_df]

            docs = list(reader.read(file_path, uuid4(), uuid4(), [], []))
            assert len(docs) == 1
            assert "foo" in docs[0].text


class TestAudioReader:
    def test_read_success_mocked(self):
        reader = AudioReader()

        mock_chunks = [{"text": "Audio Content", "timestamp_start": "00:00"}]

        # Correctly patching the service wrapper used inside the method
        with (
            patch("app.services.gemini_audio_service.GeminiAudioService.transcribe_file", new_callable=MagicMock),
            patch("asyncio.run", return_value=mock_chunks),
            patch("asyncio.get_running_loop", side_effect=RuntimeError),
        ):

            docs = list(reader.read("audio.mp3", uuid4(), uuid4(), [], []))
            assert len(docs) == 1
            assert "Audio Content" in docs[0].text


class TestReaderFactory:
    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024)
    def test_get_csv(self, mock_size, mock_exists):
        reader = ReaderFactory.get_reader("data.csv")
        assert isinstance(reader, CSVReader)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize")
    def test_get_threshold_switch(self, mock_size, mock_exists):
        # > 50 MB
        mock_size.return_value = 60 * 1024 * 1024
        assert isinstance(ReaderFactory.get_reader("Log.txt"), TextStreamReader)

        # < 50 MB
        mock_size.return_value = 10 * 1024
        assert isinstance(ReaderFactory.get_reader("Log.txt"), StandardReader)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=100)
    def test_legacy_format_rejection(self, mock_size, mock_exists):
        with pytest.raises(FunctionalError) as exc:
            ReaderFactory.get_reader("memo.doc")
        assert "UNSUPPORTED_FORMAT" in exc.value.error_code


class TestStandardReader:
    def test_read_iterative(self):
        reader = StandardReader()
        mock_doc = MagicMock()
        mock_doc.text = "Content"
        mock_doc.metadata = {}

        with patch("app.services.ingestion.document_readers.SimpleDirectoryReader") as MockSDR:
            MockSDR.return_value.load_data.return_value = [mock_doc]

            docs = list(reader.read("doc.pdf", uuid4(), uuid4(), [], []))
            assert len(docs) == 1

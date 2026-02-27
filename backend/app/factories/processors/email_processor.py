from __future__ import annotations

import email
import logging
from datetime import datetime
from email import policy
from pathlib import Path
from typing import List, Optional

from app.core.exceptions import TechnicalError
from app.factories.processors.base import DocumentMetadata, FileProcessor, ProcessedDocument

logger = logging.getLogger(__name__)


class EmailProcessor(FileProcessor):
    """
    Processor for Emails (.eml, .msg).
    Uses standard library for .eml and 'extract-msg' for .msg.
    """

    def __init__(self) -> None:
        super().__init__(max_file_size_bytes=50 * 1024 * 1024)

    def get_supported_extensions(self) -> List[str]:
        return ["eml", "msg"]

    async def process(self, file_path: str, ai_provider: Optional[str] = None) -> List[ProcessedDocument]:
        """
        Parse email and extract content/metadata.
        """
        path = await self._validate_file_path(file_path)
        ext = path.suffix.lower()

        try:
            if ext == ".msg":
                return self._process_msg(path)
            elif ext == ".eml":
                return self._process_eml(path)
            else:
                raise ValueError(f"Unsupported email format: {ext}")

        except Exception as e:
            logger.error(f"Email Processing Failed: {path.name} | {e}", exc_info=True)
            raise TechnicalError(f"Failed to process email: {e}")

    def _process_eml(self, path: Path) -> List[ProcessedDocument]:
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        subject = msg.get("subject", "No Subject")
        sender = msg.get("from", "Unknown")
        date = msg.get("date", "")

        # Extract body
        body = ""
        if msg.is_multipart():
            # content type text/plain
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body += part.get_content()
                    except:
                        pass  # decoding error
        else:
            body = msg.get_content()

        content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"

        return [
            ProcessedDocument(
                content=content,
                metadata={
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                    "page_number": 1,
                    "source_type": "email",
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                },
                success=True,
            )
        ]

    def _process_msg(self, path: Path) -> List[ProcessedDocument]:
        try:
            import extract_msg
        except ImportError:
            raise TechnicalError("extract-msg library not installed. Cannot process .msg files.")

        msg = extract_msg.Message(str(path))

        subject = msg.subject
        sender = msg.sender
        date = str(msg.date)
        body = msg.body

        content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\n{body}"

        # Must close msg to release file handle
        msg.close()

        return [
            ProcessedDocument(
                content=content,
                metadata={
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                    "page_number": 1,
                    "source_type": "email",
                    "subject": subject,
                    "sender": sender,
                    "date": date,
                },
                success=True,
            )
        ]
